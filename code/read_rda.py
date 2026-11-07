"""Minimal reader for R .rda files (XDR serialization, v2/v3). Handles data frames."""
import bz2, gzip, struct, sys

class R:
    def __init__(self, b):
        self.b = b; self.i = 0; self.refs = []
    def int(self):
        v = struct.unpack('>i', self.b[self.i:self.i+4])[0]; self.i += 4; return v
    def dbl(self, n):
        v = struct.unpack('>%dd' % n, self.b[self.i:self.i+8*n]); self.i += 8*n; return list(v)
    def ints(self, n):
        v = struct.unpack('>%di' % n, self.b[self.i:self.i+4*n]); self.i += 4*n; return list(v)
    def length(self):
        n = self.int()
        if n == -1:
            hi = self.int(); lo = self.int(); n = (hi << 32) | lo
        return n
    def item(self):
        flags = self.int()
        t = flags & 0xFF
        has_attr = bool(flags & 512); has_tag = bool(flags & 1024)
        if t == 254: return None                       # NILVALUE
        if t in (253, 242, 241, 251, 252, 247): return ('special', t)
        if t == 255:
            idx = flags >> 8
            if idx == 0: idx = self.int()
            return self.refs[idx-1]
        if t == 1:                                      # SYMSXP
            s = self.item(); self.refs.append(s); return s
        if t == 9:                                      # CHARSXP
            n = self.int()
            if n == -1: return None
            s = self.b[self.i:self.i+n]; self.i += n
            try: return s.decode('utf-8')
            except: return s.decode('latin-1')
        if t in (2, 6, 3, 5, 17):                       # pairlist-like
            out = []
            while True:
                attr = self.item() if has_attr else None
                tag = self.item() if has_tag else None
                car = self.item()
                out.append((tag, car))
                nf = self.int()
                nt = nf & 0xFF
                if nt == 254: break
                if nt not in (2, 6, 3, 5, 17):
                    self.i -= 4
                    rest = self.item(); out.append((None, rest)); break
                flags = nf; has_attr = bool(flags & 512); has_tag = bool(flags & 1024)
            return ('pairlist', out)
        if t in (10, 13):
            n = self.length(); v = self.ints(n)
            if t == 13: v = [None if x == -2147483648 else x for x in v]
            val = v
        elif t == 14:
            n = self.length(); val = self.dbl(n)
        elif t == 16:
            n = self.length(); val = [self.item() for _ in range(n)]
        elif t in (19, 20):
            n = self.length(); val = [self.item() for _ in range(n)]
        elif t == 24:
            n = self.length(); val = list(self.b[self.i:self.i+n]); self.i += n
        elif t == 238:                                  # ALTREP
            info = self.item(); state = self.item(); attr = self.item()
            cls = info[1][0][1] if info else None
            if cls in ('compact_intseq', 'compact_realseq'):
                n, start, step = state
                val = [int(start + k*step) for k in range(int(n))]
            elif cls == 'deferred_string':
                arg = state[1][0][1] if isinstance(state, tuple) else state
                val = [str(x) for x in (arg if isinstance(arg, list) else [arg])]
            else:
                val = state
            return self._wrap(val, attr)
        else:
            raise ValueError('unsupported SEXP type %d at %d' % (t, self.i))
        attr = self.item() if has_attr else None
        return self._wrap(val, attr)
    def _wrap(self, val, attr):
        if attr is None: return val
        d = {tag: v for tag, v in attr[1]}
        return {'value': val, 'attr': d}

def load(path):
    raw = open(path, 'rb').read()
    for op in (bz2.decompress, gzip.decompress, lambda x: x):
        try: raw = op(raw); break
        except Exception: continue
    assert raw[:5] in (b'RDX2\n', b'RDX3\n'), raw[:5]
    r = R(raw); r.i = 5
    assert raw[r.i:r.i+2] == b'X\n'; r.i += 2
    ver = r.int(); r.int(); r.int()
    if ver == 3:
        n = r.int(); r.i += n
    top = r.item()
    return {tag: v for tag, v in top[1]}

def to_columns(df):
    cols = df['value']; names = df['attr']['names']
    out = {}
    for n, c in zip(names, cols):
        if isinstance(c, dict) and 'levels' in c['attr']:
            lv = c['attr']['levels']
            out[n] = [None if x is None else lv[x-1] for x in c['value']]
        elif isinstance(c, dict):
            out[n] = c['value']
        else:
            out[n] = c
    return out

if __name__ == '__main__':
    objs = load(sys.argv[1])
    for k, v in objs.items():
        cols = to_columns(v)
        print(k, {c: len(x) for c, x in cols.items()})
        for c, x in cols.items(): print(' ', c, x[:3])
