#!/usr/bin/env python3
# Port of ATJ227X_firmware_tools fwu.c (v3 decoder) to Python.
import re, sys, struct

SRC = r"C:\Users\INSOER~1\AppData\Local\Temp\opencode\atj_src\atj_tables.h"

def load_arrays(path):
    txt = open(path, "r", errors="ignore").read()
    arrs = {}
    for m in re.finditer(r"(?:uint8_t|uint32_t)\s+(\w+)\[[^\]]*\]\s*=\s*\{(.*?)\}\s*;", txt, re.S):
        name = m.group(1); body = m.group(2)
        vals = [int(x, 16) for x in re.findall(r"0x[0-9a-fA-F]+", body)]
        arrs[name] = vals
    return arrs

A = load_arrays(SRC)
CHK = A["g_check_block_A_table"]
DEC_B = A["g_decode_B_table"]
CRYPT_T = A["g_crypto_table"]
CRYPT_T2 = A["g_crypto_table2"]
KEY6 = A["g_crypto_key6"]
KEY3 = A["g_crypto_key3"]
KEY4 = A["g_crypto_key4"]
EC163A = A["g_atj_ec163_a"]
KEY5 = A["g_crypto_key5"]
EC233A = A["g_atj_ec233_a"]
print("table sizes:", {k: len(v) for k, v in A.items()})

FWU_SIG = bytes([0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff,0x75])

def compute_checksum(buf):
    t = [0]*20
    for i in range(len(buf)):
        t[i % 20] ^= buf[i]
    return bytes((~x) & 0xff for x in t)

def check_block(buf, ref, size):
    return compute_checksum(buf[:size]) == bytes(ref[:20])

def decode_block_A(buf, off):
    # block = buf[off:off+1020]; 'block-1' = buf[off-1]
    pi = 32 * (buf[off+998] & 0x1f)
    key = [0]*32
    for i in range(20):
        buf[off+1000+i] ^= CHK[pi+i]
        key[i] = buf[off+1000+i]
    for i in range(20, 32):
        key[i] = key[i-20]
    for i in range(992):
        buf[off+i] ^= key[i % 32] ^ CHK[i]
    return check_block(bytes(buf[off-1:off-1+1001]), buf[off+1000:off+1000+20], 1001)

def compute_perm(keybuf, perm):
    for i in range(256):
        perm[i] = i
    perm[256] = perm[257] = 0
    idx = 0
    n = len(keybuf)
    for i in range(256):
        v = perm[i]
        idx = (v + keybuf[i % n] + idx) % 256
        perm[i] = perm[idx]
        perm[idx] = v

def decode_perm(buf, perm, size=None):
    if size is None: size = len(buf)
    idxa = perm[256]; idxb = perm[257]
    for i in range(size):
        idxa = (idxa + 1) % 256
        v = perm[idxa]
        idxb = (idxb + v) % 256
        perm[idxa] = perm[idxb]
        perm[idxb] = v
        buf[i] = buf[i] ^ perm[(v + perm[idxa]) % 256]

def decode_block_with_perm(keybuf, keylen, buf, bufsize, perm):
    compute_perm(keybuf, perm)
    decode_perm(buf, perm, bufsize)

def apply_perm(inbuf, outbuf, size, swap):
    outbuf[:size] = inbuf[:size]
    a = swap & 0xf
    b = (swap >> 4) + 16
    outbuf[a], outbuf[b] = outbuf[b], outbuf[a]

def decode_block_with_swap(keybuf, swap, buf, bufsize, perm):
    kb = bytearray(32)
    apply_perm(keybuf, kb, 32, swap)
    decode_block_with_perm(kb, 32, buf, bufsize, perm)

# ---- GF(2) polynomial arithmetic (big int) ----
class Field:
    def __init__(self, bits, poly):
        self.poly = poly
        self.mask = (1 << bits) - 1

def poly_mod(a, poly):
    pl = poly.bit_length()
    while a.bit_length() >= pl:
        a ^= poly << (a.bit_length() - pl)
    return a

def gf_mul(a, b, F):
    r = 0
    while b:
        if b & 1: r ^= a
        b >>= 1
        a <<= 1
    return poly_mod(r, F.poly)

def gf_inv(a, F):
    # extended euclid over GF(2)
    u, v = a, F.poly
    g1, g2 = 1, 0
    while u != 1:
        j = u.bit_length() - v.bit_length()
        if j < 0:
            u, v = v, u
            g1, g2 = g2, g1
            j = -j
        u ^= v << j
        g1 ^= g2 << j
    return poly_mod(g1, F.poly)

def words_to_int(words):
    v = 0
    for i, w in enumerate(words):
        v |= (w & 0xffffffff) << (32*i)
    return v

def init_ec(field_sz):
    if field_sz == 4:
        F = Field(233, (1<<233)|(1<<74)|1)
        ax = words_to_int(CRYPT_T); ay = words_to_int(CRYPT_T2); ec_a = words_to_int(EC233A)
    elif field_sz == 5:
        F = Field(163, (1<<163)|(1<<7)|(1<<6)|(1<<3)|1)
        ax = words_to_int(KEY3); ay = words_to_int(KEY4); ec_a = words_to_int(EC163A)
    else:
        raise ValueError("bad field_sz %d" % field_sz)
    return F, (ax, ay), ec_a

def ec_double(P, F, ec_a):
    x, y = P
    v4 = gf_inv(x, F)
    v5 = gf_mul(v4, y, F)
    v2 = x ^ v5
    v4 = v2 ^ ec_a
    v3 = gf_mul(v2, v2, F)
    rx = v4 ^ v3
    v4 = v2 ^ 1
    v5 = gf_mul(v4, rx, F)
    v6 = gf_mul(x, x, F)
    ry = v5 ^ v6
    return (rx, ry)

def ec_add(P1, P2, F, ec_a):
    x1, y1 = P1; x2, y2 = P2
    v5 = y1 ^ y2
    v6 = x1 ^ x2
    v7 = gf_inv(v6, F)
    v3 = gf_mul(v7, v5, F)
    v5 = v3 ^ ec_a
    v4 = gf_mul(v3, v3, F)
    v7 = v5 ^ v4
    rx = v7 ^ v6
    v5 = x1 ^ rx
    v6 = rx ^ y1
    v7 = gf_mul(v5, v3, F)
    ry = v7 ^ v6
    return (rx, ry)

def ec_mult(n_words, P, F, ec_a):
    n = words_to_int(n_words)
    if n == 0:
        return (0, 0)
    R = None
    Q = P
    for bit in range(n.bit_length()-1, -1, -1):
        if R is None:
            R = Q
        else:
            R = ec_double(R, F, ec_a)
            R = ec_add(R, Q, F, ec_a)
        if not (n >> bit) & 1:
            # standard double-and-add: we added Q only if bit set
            pass
    # redo properly
    R = (0, 0)
    started = False
    for bit in range(n.bit_length()-1, -1, -1):
        if started:
            R = ec_double(R, F, ec_a)
        else:
            started = True
            R = (0, 0)
        if (n >> bit) & 1:
            R = Q if R == (0,0) else ec_add(R, Q, F, ec_a)
    return R

def crypto4(a1, pt_x, pt_y, mult_words, F, ec_a):
    P = ec_mult(mult_words, (pt_x, pt_y), F, ec_a)
    rx, ry = P
    xb = rx.to_bytes(64, "little")
    yb = ry.to_bytes(64, "little")
    sz = min(NRB2 - 1, 32)
    for i in range(sz):
        a1[i] ^= xb[i]
    for i in range(sz, 32):
        a1[i] ^= yb[i - sz]

NRB2 = 0

def process_block_A(bb):
    global g_crypto_info_byte, g_decode_buffer, g_decode_buffer2, NRB2
    ok = decode_block_A(bb, 4)
    print("  BlockA check:", ok)
    # subblock A = bb[0:0x128]
    field_byte = bb[276]
    if field_byte == 2: sz = 233
    elif field_byte == 3: sz = 163
    else: sz = None
    nr_bytes2 = (sz // 8 + (1 if sz % 8 else 0)) if sz else 0
    NRB2 = nr_bytes2
    tmp = 2 * nr_bytes2 + 38
    off = 1004 - tmp + 5
    g_crypto_info_byte = bb[off-1]
    g_decode_buffer = bytearray(bb[off:off+nr_bytes2])
    off2 = nr_bytes2 + off
    g_decode_buffer2 = bytearray(bb[off2:off2+nr_bytes2])
    print("  field_byte", field_byte, "sz", sz, "nr_bytes2", nr_bytes2, "info_byte", g_crypto_info_byte)
    return ok

g_key_B = bytearray(20)
def decode_key_B(buf, off, buf2, key):
    for i in range(20):
        v = buf[off+i] ^ DEC_B[i]
        key[i] = v
        buf[off+i] = v ^ buf2[i % 16]

def decode_block_B(buf, off, key, size):
    decode_key_B(buf, off+size, key, g_key_B)
    decode_block_with_perm(g_key_B, 20, memoryview(buf)[off:off+size], size, [0]*258)

g_decode_buffer3 = bytearray()
def process_block_B(sb):
    global g_decode_buffer3
    off = 3
    decode_key_B(sb, off+489, sb[4:4+0x128], g_key_B)  # buf2 = subblock_A+4
    decode_block_with_perm(g_key_B, 20, sb, 489, [0]*258)  # placeholder (will be redone)
    # NOTE: C calls decode_block_B(block+3, subA+4, 489) which uses perm global
    # We'll just replicate with a fresh perm
    return True

def process_block_B_real(sb, subA):
    # block+3, buf2 = subA+4, key = g_key_B
    off = 3
    decode_key_B(sb, off+489, subA[4:], g_key_B)
    perm = [0]*258
    decode_block_with_perm(g_key_B, 20, memoryview(sb)[off:off+489], 489, perm)
    word = struct.unpack_from("<H", sb, 3)[0]
    chk = check_block(bytes(sb[0:492]), sb[492:512], 492)
    if not chk: return None
    g_decode_buffer3 = bytearray()
    offset = struct.unpack_from("<H", sb, 13)[0] + 16
    return bytearray(sb[offset:offset+NRB2])

def get_key_fwu_v3(buf):
    ba = buf[0x1ee] & 0xf
    bb = buf[0x1fe] & 0xf
    print("Crypto block A=%d B=%d" % (ba+2, ba+bb+5))
    blockA = buf[494] & 0xf
    blockB = buf[510] & 0xf
    bigblock = bytearray(buf[512*(blockA+2): 512*(blockA+2)+1024])
    process_block_A(bigblock)
    smallblock = bytearray(buf[512*(blockA+blockB+5): 512*(blockA+blockB+5)+512])
    db3 = process_block_B_real(smallblock, bigblock[:0x128])
    if db3 is None:
        print("block B check fail"); return None, None
    # crypto hdr at buf[42]: field0[16], unk(1), key[32]
    unk = buf[42+16]
    print("crypto unk", unk)
    key = bytearray(buf[42+17:42+17+32])
    F, (px, py), ec_a = init_ec(g_crypto_info_byte)
    nx2 = NRB2
    pt_x = words_to_int(list(struct.unpack_from("<%dI"%(nx2//4+ (1 if nx2%4 else 0)), buf, 91)))
    # careful: ptrs.x = buf+91 (nr_bytes2 bytes), ptrs.y = buf+91+nr_bytes2
    sx = bytes(buf[91:91+nx2]); sy = bytes(buf[91+nx2:91+2*nx2])
    pt_x = int.from_bytes(sx, "little"); pt_y = int.from_bytes(sy, "little")
    mult_words = list(struct.unpack_from("<%dI"%(len(db3)//4 + (1 if len(db3)%4 else 0)), db3 + b"\x00"*3, 0)) if len(db3)%4 else list(struct.unpack_from("<%dI"%(len(db3)//4), db3, 0))
    crypto4(key, pt_x, pt_y, mult_words, F, ec_a)
    # offset = nr_words + 91; nr_words = 2*nr_bytes2
    off = 2*NRB2 + 91
    decode_block_with_swap(key, 0, memoryview(buf)[off:off+(512-off)], 512-off, [0]*258)
    return key, (blockA, blockB)

def decrypt_fwu_v3(buf, size):
    key, blk = get_key_fwu_v3(buf)
    if key is None: return None
    blockA, blockB = blk
    fw_size = struct.unpack_from("<I", buf, 16)[0]
    outsize = fw_size - 2048
    offsetA = (blockA+1) << 9
    offsetB = (blockB+1) << 9
    tmp = bytearray()
    tmp += buf[512:512+offsetA]
    tmp += buf[offsetA+1536: offsetA+1536+offsetB]
    tmp += buf[offsetA+1536+offsetB+512: offsetA+1536+offsetB+512 + (outsize-offsetA-offsetB)]
    perm = [0]*258
    compute_perm(key, perm)
    decode_perm(tmp, perm, outsize)
    return tmp

def main():
    path = sys.argv[1]; out = sys.argv[2]
    d = bytearray(open(path,"rb").read())
    assert d[:16] == FWU_SIG, "no FWU sig"
    fw_size = struct.unpack_from("<I", d, 16)[0]
    blk = struct.unpack_from("<I", d, 20)[0]
    print("fw_size", fw_size, "block_size", blk, "version", hex(d[24]), "unk", hex(d[25]))
    res = decrypt_fwu_v3(d, len(d))
    if res is None:
        print("decode failed"); return
    print("decoded size", len(res))
    open(out,"wb").write(res)
    print("wrote", out, "first:", res[:32].hex())

if __name__ == "__main__":
    main()
