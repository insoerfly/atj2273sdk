#!/usr/bin/env python3
# Minimal MIPS32 (little-endian) interpreter, enough to run Actions boot modules.
# No external deps. Page-based sparse memory.
import struct, sys, collections

PAGE = 0x1000

class Mem:
    def __init__(self):
        self.pages = {}
    def _pg(self, a, create=False):
        p = a >> 12
        pg = self.pages.get(p)
        if pg is None and create:
            pg = bytearray(PAGE); self.pages[p] = pg
        return pg
    def load(self, addr, data):
        off = 0
        while off < len(data):
            a = addr + off
            pg = self._pg(a, True)
            o = a & (PAGE-1); n = min(PAGE-o, len(data)-off)
            pg[o:o+n] = data[off:off+n]; off += n
    def r8(self, a):
        pg = self.pages.get(a >> 12)
        return pg[a & (PAGE-1)] if pg else 0
    def w8(self, a, v):
        self._pg(a, True)[a & (PAGE-1)] = v & 0xff
    def r16(self, a): return self.r8(a) | (self.r8(a+1) << 8)
    def r32(self, a): return self.r8(a) | (self.r8(a+1)<<8) | (self.r8(a+2)<<16) | (self.r8(a+3)<<24)
    def w16(self, a, v): self.w8(a,v); self.w8(a+1,v>>8)
    def w32(self, a, v):
        self.w8(a,v); self.w8(a+1,v>>8); self.w8(a+2,v>>16); self.w8(a+3,v>>24)

def s32(v): v&=0xFFFFFFFF; return v-0x100000000 if v&0x80000000 else v

class CPU:
    def __init__(self, mem):
        self.m = mem
        self.r = [0]*32
        self.hi = 0; self.lo = 0
        self.pc = 0
        self.hooks = {}     # addr -> fn(cpu)->None (called INSTEAD of executing at addr)
        self.trace = False
        self.icount = 0
        self.log = []
    def rd(self, i): return self.r[i]
    def wr(self, i, v):
        if i: self.r[i] = v & 0xFFFFFFFF
    def step(self):
        pc = self.pc
        if pc in self.hooks:
            self.hooks[pc](self); return
        w = self.m.r32(pc)
        nxt = (pc + 4) & 0xFFFFFFFF
        op = w >> 26
        rs = (w>>21)&31; rt=(w>>16)&31; rd=(w>>11)&31; sa=(w>>6)&31; fn=w&63
        imm = w & 0xFFFF; simm = imm-0x10000 if imm&0x8000 else imm
        if op == 0:
            if fn==0x00: self.wr(rt and 0 or 0,0); self.wr(rd, self.rd(rt)<<sa)  # sll (rt may be 0)
            elif fn==0x02: self.wr(rd, self.rd(rt)>>sa)
            elif fn==0x03: self.wr(rd, s32(self.rd(rt))>>sa & 0xFFFFFFFF)
            elif fn==0x04: self.wr(rd, self.rd(rt) << (self.rd(rs)&31))
            elif fn==0x06: self.wr(rd, self.rd(rt) >> (self.rd(rs)&31))
            elif fn==0x07: self.wr(rd, (s32(self.rd(rt)) >> (self.rd(rs)&31)) & 0xFFFFFFFF)
            elif fn==0x08: nxt = self.rd(rs)
            elif fn==0x09:
                nxt = self.rd(rs)
                if rd: self.wr(rd, (pc+8)&0xFFFFFFFF)
            elif fn==0x0c or fn==0x0d: pass  # syscall/break
            elif fn==0x10: self.wr(rd, self.hi)
            elif fn==0x11: self.hi = self.rd(rs)
            elif fn==0x12: self.wr(rd, self.lo)
            elif fn==0x13: self.lo = self.rd(rs)
            elif fn==0x18:
                p = s32(self.rd(rs))*s32(self.rd(rt)); self.lo=p&0xFFFFFFFF; self.hi=(p>>32)&0xFFFFFFFF
            elif fn==0x19:
                p = self.rd(rs)*self.rd(rt); self.lo=p&0xFFFFFFFF; self.hi=(p>>32)&0xFFFFFFFF
            elif fn==0x1a:
                a,b=self.rd(rs),self.rd(rt)
                if b: q=s32(a)//s32(b); rr=s32(a)%s32(b); self.lo=q&0xFFFFFFFF; self.hi=rr&0xFFFFFFFF
            elif fn==0x1b:
                a,b=self.rd(rs),self.rd(rt)
                if b: self.lo=a//b; self.hi=a%b
            elif fn==0x20: self.wr(rd, (s32(self.rd(rs))+s32(self.rd(rt)))&0xFFFFFFFF)
            elif fn==0x21: self.wr(rd, (self.rd(rs)+self.rd(rt))&0xFFFFFFFF)
            elif fn==0x22: self.wr(rd, (s32(self.rd(rs))-s32(self.rd(rt)))&0xFFFFFFFF)
            elif fn==0x23: self.wr(rd, (self.rd(rs)-self.rd(rt))&0xFFFFFFFF)
            elif fn==0x24: self.wr(rd, self.rd(rs)&self.rd(rt))
            elif fn==0x25: self.wr(rd, self.rd(rs)|self.rd(rt))
            elif fn==0x26: self.wr(rd, self.rd(rs)^self.rd(rt))
            elif fn==0x27: self.wr(rd, (~(self.rd(rs)|self.rd(rt)))&0xFFFFFFFF)
            elif fn==0x2a: self.wr(rd, 1 if s32(self.rd(rs))<s32(self.rd(rt)) else 0)
            elif fn==0x2b: self.wr(rd, 1 if self.rd(rs)<self.rd(rt) else 0)
            else: raise RuntimeError(f"special fn {fn:#x} @ {pc:#x}")
        elif op == 0x01:
            rt_ = rt
            take = False
            if rt_==0x00: take = s32(self.rd(rs))<0
            elif rt_==0x01: take = s32(self.rd(rs))>=0
            elif rt_==0x10: take = s32(self.rd(rs))<0; self.wr(31,(pc+8)&0xFFFFFFFF)
            elif rt_==0x11: take = s32(self.rd(rs))>=0; self.wr(31,(pc+8)&0xFFFFFFFF)
            elif rt_ in (0x02,0x03): take = False; # bltzl/bgezl likely
            elif rt_ in (0x12,0x13): self.wr(31,(pc+8)&0xFFFFFFFF)
            else: take=False
            if take: nxt = (pc+4+(simm<<2))&0xFFFFFFFF
            else: nxt = (pc+8)&0xFFFFFFFF if rt_ in (0x02,0x03,0x12,0x13) else (pc+4)&0xFFFFFFFF
        elif op == 0x02: nxt = ((pc+4)&0xF0000000) | ((w&0x3FFFFFF)<<2)
        elif op == 0x03:
            self.wr(31,(pc+8)&0xFFFFFFFF)
            nxt = ((pc+4)&0xF0000000) | ((w&0x3FFFFFF)<<2)
        elif op == 0x04:
            nxt = (pc+4+(simm<<2))&0xFFFFFFFF if self.rd(rs)==self.rd(rt) else (pc+4)&0xFFFFFFFF
        elif op == 0x05:
            nxt = (pc+4+(simm<<2))&0xFFFFFFFF if self.rd(rs)!=self.rd(rt) else (pc+4)&0xFFFFFFFF
        elif op == 0x06:
            nxt = (pc+4+(simm<<2))&0xFFFFFFFF if s32(self.rd(rs))<=0 else (pc+4)&0xFFFFFFFF
        elif op == 0x07:
            nxt = (pc+4+(simm<<2))&0xFFFFFFFF if s32(self.rd(rs))>0 else (pc+4)&0xFFFFFFFF
        elif op == 0x08: self.wr(rt, (s32(self.rd(rs))+simm)&0xFFFFFFFF)
        elif op == 0x09: self.wr(rt, (self.rd(rs)+simm)&0xFFFFFFFF)
        elif op == 0x0a: self.wr(rt, 1 if s32(self.rd(rs))<simm else 0)
        elif op == 0x0b: self.wr(rt, 1 if self.rd(rs)<(simm&0xFFFFFFFF) else 0)
        elif op == 0x0c: self.wr(rt, self.rd(rs)&imm)
        elif op == 0x0d: self.wr(rt, self.rd(rs)|imm)
        elif op == 0x0e: self.wr(rt, self.rd(rs)^imm)
        elif op == 0x0f: self.wr(rt, (imm<<16)&0xFFFFFFFF)
        elif op in (0x10,0x11,0x12,0x13):
            if rs==0:  # mfc0/mtc0/cfc
                if rt: self.wr(rt,0)
            else: pass
        elif op == 0x1c:  # special2
            if fn==0x02:  # mul
                self.wr(rd, (s32(self.rd(rs))*s32(self.rd(rt)))&0xFFFFFFFF)
            elif fn==0x00:  # madd
                p=s32(self.rd(rs))*s32(self.rd(rt)); v=((self.hi<<32)|self.lo)+p; self.lo=v&0xFFFFFFFF; self.hi=(v>>32)&0xFFFFFFFF
            elif fn==0x01:  # maddu
                p=self.rd(rs)*self.rd(rt); v=((self.hi<<32)|self.lo)+p; self.lo=v&0xFFFFFFFF; self.hi=(v>>32)&0xFFFFFFFF
            elif fn==0x04:  # msub
                p=s32(self.rd(rs))*s32(self.rd(rt)); v=((self.hi<<32)|self.lo)-p; self.lo=v&0xFFFFFFFF; self.hi=(v>>32)&0xFFFFFFFF
            else: raise RuntimeError(f"special2 fn {fn:#x} @ {pc:#x}")
        elif op == 0x1f:  # special3 (seb/seh/ext/ins) - approximate
            if fn==0x20:
                if sa==16: v=self.rd(rt)&0xFF; v=v-0x100 if v&0x80 else v; self.wr(rd,v&0xFFFFFFFF)
                elif sa==24: v=self.rd(rt)&0xFFFF; v=v-0x10000 if v&0x8000 else v; self.wr(rd,v&0xFFFFFFFF)
                else: self.wr(rd,self.rd(rt))
            elif fn==0x00 and sa==0:  # ext
                sz=rd+1; off=sa
                v=(self.rd(rs)>>off)&((1<<sz)-1); self.wr(rt,v)
            elif fn==0x04:  # ins
                pass
            else: raise RuntimeError(f"special3 fn {fn:#x} sa {sa} @ {pc:#x}")
        elif op in (0x20,0x24,0x21,0x25,0x23,0x2b,0x28,0x29,0x2a):
            addr=(self.rd(rs)+simm)&0xFFFFFFFF
            if op==0x20: self.wr(rt, s32(self.m.r8(addr))&0xFFFFFFFF)         # lb
            elif op==0x24: self.wr(rt, self.m.r8(addr))                      # lbu
            elif op==0x21: self.wr(rt, s32(self.m.r16(addr))&0xFFFFFFFF)     # lh
            elif op==0x25: self.wr(rt, self.m.r16(addr))                     # lhu
            elif op==0x23: self.wr(rt, self.m.r32(addr))                     # lw
            elif op==0x2b: self.m.w32(addr, self.rd(rt))                     # sw
            elif op==0x28: self.m.w8(addr, self.rd(rt))                      # sb
            elif op==0x29: self.m.w16(addr, self.rd(rt))                     # sh
            elif op==0x2a:  # swl
                a=addr; b=self.rd(rt); cur=self.m.r32(a&~3)
                sh=(a&3)*8
                if a&3==0: cur=(cur&0xFFFFFF00)|(b&0xFF)
                elif a&3==1: cur=(cur&0xFFFF0000)|(b&0xFFFF)
                elif a&3==2: cur=(cur&0xFF000000)|(b&0xFFFFFF)
                else: cur=b
                self.m.w32(a&~3,cur)
        elif op == 0x22:  # lwl
            a=(self.rd(rs)+simm)&0xFFFFFFFF; cur=self.m.r32(a&~3); b=self.rd(rt)
            if a&3==0: v=(cur&0xFFFFFF00)|(b>>24)
            elif a&3==1: v=(cur&0xFFFF0000)|(b>>16)
            elif a&3==2: v=(cur&0xFF000000)|(b>>8)
            else: v=b
            self.wr(rt,v&0xFFFFFFFF)
        elif op == 0x26:  # lwr
            a=(self.rd(rs)+simm)&0xFFFFFFFF; cur=self.m.r32(a&~3); b=self.rd(rt)
            if a&3==0: v=b
            elif a&3==1: v=(b<<8)|(cur&0xFF)
            elif a&3==2: v=(b<<16)|(cur&0xFFFF)
            else: v=(b<<24)|(cur&0xFFFFFF)
            self.wr(rt,v&0xFFFFFFFF)
        else:
            raise RuntimeError(f"op {op:#x} word {w:08x} @ {pc:#x}")
        self.pc = nxt & 0xFFFFFFFF
        self.icount += 1

def main():
    pass

if __name__ == "__main__":
    main()
