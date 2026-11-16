@ Drobo B800i launcher, run from U-Boot with `go <addr>`.
@ The zImage is appended directly after this stub (see Makefile).
@
@ 1. Optionally moves the SoC register window from REMAP_FROM to 0xf1000000,
@    where mainline Linux expects it (only in the -d0 build; REMAP_FROM
@    is the old base + 0x20000, the bridge block holding that register).
@ 2. Prints "B800i stub OK" on UART0 so you know it ran.
@ 3. Cleans/invalidates L1 caches and turns the MMU and caches off.
@ 4. Writes a minimal ATAG list at 0x100 (core + MEM_MB of RAM at 0).
@ 5. Jumps to the zImage with r0=0, r1=machine 9001, r2=0x100.
	.syntax unified
	.arm
	.text
	.global _start

#ifndef MEM_MB
#define MEM_MB 256
#endif
#define REGS	0xf1000000
#define MACH	9001

_start:
	mrs	r0, cpsr
	bic	r0, r0, #0x1f
	orr	r0, r0, #0xd3		@ SVC mode, IRQ+FIQ off
	msr	cpsr_c, r0

#ifdef REMAP_FROM
	ldr	r0, =REMAP_FROM
	ldr	r1, =REGS
	str	r1, [r0, #0x80]		@ internal regs base reg lives at +0x20080
#endif

	ldr	r4, =REGS + 0x12000	@ UART0
	adr	r5, msg
1:	ldrb	r1, [r5], #1
	cmp	r1, #0
	beq	2f
3:	ldr	r2, [r4, #0x14]		@ LSR
	tst	r2, #0x20		@ THR empty
	beq	3b
	str	r1, [r4]
	b	1b
2:
	@ clean+invalidate D-cache (ARM926/Feroceon test-clean-invalidate loop)
4:	mrc	p15, 0, r15, c7, c14, 3
	bne	4b
	mov	r0, #0
	mcr	p15, 0, r0, c7, c5, 0	@ invalidate I-cache
	mcr	p15, 0, r0, c7, c10, 4	@ drain write buffer
	mrc	p15, 0, r0, c1, c0, 0
	bic	r0, r0, #0x0005		@ MMU off, D-cache off
	bic	r0, r0, #0x1000		@ I-cache off
	mcr	p15, 0, r0, c1, c0, 0
	mov	r0, #0
	mcr	p15, 0, r0, c8, c7, 0	@ flush TLBs

	@ ATAG list at 0x100
	mov	r2, #0x100
	mov	r3, r2
	ldr	r0, =0x00000002		@ ATAG_CORE, size 2 (no payload)
	str	r0, [r3], #4
	ldr	r0, =0x54410001
	str	r0, [r3], #4
	mov	r0, #4			@ ATAG_MEM, size 4
	str	r0, [r3], #4
	ldr	r0, =0x54410002
	str	r0, [r3], #4
	ldr	r0, =(MEM_MB << 20)
	str	r0, [r3], #4
	mov	r0, #0			@ start 0
	str	r0, [r3], #4
	str	r0, [r3], #4		@ ATAG_NONE
	str	r0, [r3], #4

	mov	r0, #0
	ldr	r1, =MACH
	adr	r4, payload
	mov	pc, r4

msg:	.asciz	"\r\nB800i stub OK, starting Linux...\r\n"
	.ltorg
	.balign	64
payload:
