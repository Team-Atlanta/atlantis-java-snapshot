#!/usr/bin/env python3

with open('OpcodePrep.txt', 'rt') as f:
    lines = f.readlines()


lines = [line.split(';')[0] for line in lines if 'final int' in line]

def process_lines(lines):
    l = []
    for line in lines:
        int_idx = line.find('int ')
        target = [l.strip() for l in line[int_idx+4:].split('=')]
        l.append(target)
    return l

cases = process_lines(lines)

case_array = []
for case in cases:
    s = f'            case {case[1]} : return "{case[0]}";'
    case_array.append(s)


java_code_head = """package com.oracle.truffle.espresso.bytecode;

public final class Opcodes {
    public static String getOpcodeName(int opcode) {
        switch (opcode) {
"""

java_code_tail = """
        }
    }
}"""


with open('Opcodes.java', 'wt') as f:
    f.write(java_code_head)
    f.write('\n'.join(case_array))
    f.write('\n            default: return null;\n')
    f.write(java_code_tail)
