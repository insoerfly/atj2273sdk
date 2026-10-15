#!/usr/bin/env python3
# Minimal pure-Python MIPS32 little-endian disassembler (no deps).
# Usage: python mipsdis.py file.bin [start] [count] [vaddr_base]
import sys, struct

R = ["zero","at","v0","v1","a0","a1","a2","a3","t0","t1","t2","t3","t4","t5","t6","t7",
     "s0","s1","s2","s3","s4","s5","s6","s7","t8","t9","k0","k1","gp","sp","fp","ra"]
SPECIAL = {0x00:"sll",0x02:"srl",0x03:"sra",0x04:"sllv",0x06:"srlv",0x07:"srav",
 0x08:"jr",0x09:"jalr",0x0a:"movz",0x0b:"movn",0x0c:"syscall",0x0d:"break",0x0f:"sync",
 0x10:"mfhi",0x11:"mthi",0x12:"mflo",0x13:"mtlo",0x18:"mult",0x19:"multu",0x1a:"div",0x1b:"divu",
 0x20:"add",0x21:"addu",0x22:"sub",0x23:"subu",0x24:"and",0x25:"or",0x26:"xor",0x27:"nor",
 0x2a:"slt",0x2b:"sltu",0x30:"tge",0x31:"tgeu",0x32:"tlt",0x33:"tltu",0x34:"teq",0x36:"tne"}
REGIMM = {0x00:"bltz",0x01:"bgez",0x02:"bltzl",0x03:"bgezl",0x10:"bltzal",0x11:"bgezal",
 0x12:"bltzall",0x13:"bgezall"}
MEM = {0x20:"lb",0x21:"lh",0x22:"lwl",0x23:"lw",0x24:"lbu",0x25:"lhu",0x26:"lwr",0x27:"lwu",
 0x28:"sb",0x29:"sh",0x2a:"swl",0x2b:"swr",0x2c:"ll",0x2e:"lwc2",0x2f:"cache",0x3f:"sd"}
IMM = {0x08:"addi",0x09:"addiu",0x0a:"slti",0x0b:"sltiu",0x0c:"andi",0x0d:"ori",0x0e:"xori",0x0f:"lui"}
BR  = {0x04:"beq",0x05:"bne",0x06:"blez",0x07:"bgtz",0x14:"beql",0x15:"bnel",0x16:"blezl",0x17:"bgtzl"}

def sx(v,n):
    m=1<<(n-1); return (v^m)-m

def dis(w,pc):
    op=w>>26; rs=(w>>21)&31; rt=(w>>16)&31; rd=(w>>11)&31; sa=(w>>6)&31; fn=w&63; imm=w&0xffff
    tgt=(pc+4&0xf0000000)|((w&0x3ffffff)<<2)
    if op==0:
        if fn==0x00: return f"sll {R[rd]},{R[rt]},{sa}"
        if fn==0x02: return f"srl {R[rd]},{R[rt]},{sa}"
        if fn==0x03: return f"sra {R[rd]},{R[rt]},{sa}"
        if fn==0x08: return f"jr {R[rs]}"
        if fn==0x09: return f"jalr {R[rd]},{R[rs]}"
        if fn in (0x18,0x19): return f"{SPECIAL[fn]} {R[rs]},{R[rt]}"
        if fn in (0x1a,0x1b): return f"{SPECIAL[fn]} {R[rs]},{R[rt]}"
        if fn==0x10: return f"mfhi {R[rd]}"
        if fn==0x12: return f"mflo {R[rd]}"
        if fn in (0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x2a,0x2b):
            return f"{SPECIAL[fn]} {R[rd]},{R[rs]},{R[rt]}"
        if fn==0x0c: return "syscall"
        if fn==0x0d: return "break"
        return f".word {w:08x} (special {fn:#x})"
    if op==0x01:
        return f"{REGIMM.get(rt,'regimm%02x'%rt)} {R[rs]},{sx(imm,16)}"
    if op==0x02: return f"j {tgt:#x}"
    if op==0x03: return f"jal {tgt:#x}"
    if op in BR:
        return f"{BR[op]} {R[rs]},{R[rt]},{sx(imm,16)}"
    if op in IMM:
        if op==0x0f: return f"lui {R[rt]},{imm:#x}"
        if op in (0x0c,0x0d,0x0e): return f"{IMM[op]} {R[rt]},{R[rs]},{imm:#x}"
        return f"{IMM[op]} {R[rt]},{R[rs]},{sx(imm,16)}"
    if op in MEM or op in (0x23,0x2b,0x28,0x29):
        return f"{MEM[op]} {R[rt]},{sx(imm,16)}({R[rs]})"
    return f".word {w:08x} (op {op:#x})"

def main():
    fn=sys.argv[1]; start=int(sys.argv[2],0) if len(sys.argv)>2 else 0
    cnt=int(sys.argv[3],0) if len(sys.argv)>3 else 40
    base=int(sys.argv[4],0) if len(sys.argv)>4 else 0
    d=open(fn,"rb").read()
    for i in range(cnt):
        off=start+i*4
        if off+4>len(d): break
        w=struct.unpack_from("<I",d,off)[0]
        pc=base+off
        print(f"{pc:08x}: {w:08x}  {dis(w,pc)}")

if __name__=="__main__":
    main()
