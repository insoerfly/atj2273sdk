/*
 * atj227x_regs.h - peripheral base addresses for Actions ATJ227X / ATJ2273x.
 *
 * Facts distilled from the ATJ227X datasheet (v1.0, 2010-11-26). Not affiliated
 * with Actions Semiconductor; provided as a convenience for register-level work.
 * Verify against your exact part (ATJ2273S vs ATJ2273B) before relying on it.
 *
 * MIPS: peripherals are uncached via KSEG1 = physical | 0xA0000000.
 */
#ifndef __ATJ227X_REGS_H__
#define __ATJ227X_REGS_H__

/* Standard MIPS segments */
#define KSEG0_BASE      0x80000000u   /* kernel, cached   */
#define KSEG1_BASE      0xA0000000u   /* kernel, uncached */
#define KSEG1(p)        ((volatile unsigned int *)((unsigned int)(p) | KSEG1_BASE))

/* --- register block bases (physical) --- */
#define ATJ_INTC_BASE       0x10000000u
#define ATJ_INTC2_BASE      0x10020000u
#define ATJ_RTC_BASE        0x10018000u
#define ATJ_TP_BASE         0x10120000u   /* touch panel / 2ch ADC */
#define ATJ_UART0_BASE      0x10160000u
#define ATJ_UART1_BASE      0x10168000u
#define ATJ_IRC_BASE        0x10160050u
#define ATJ_I2C_BASE        0x10180000u
#define ATJ_KEY_BASE        0x101A0000u   /* key scan (4x2) */
#define ATJ_GPIO_BASE       0x101C0000u   /* GPIO / MFP / PWM */
#define ATJ_SPI0_BASE       0x10250000u
#define ATJ_SPI1_BASE       0x10258000u
#define ATJ_LCD_BASE        0x102A0000u   /* LCD controller */
#define ATJ_VDCSI_BASE      0x102B8000u   /* video-in / CMOS sensor */

/* --- a few known offsets --- */
#define ATJ_KEY_CTL         0x00u         /* key scan control */
#define ATJ_KEY_DAT         0x04u         /* key scan data    */

/* Convenience KSEG1 pointers */
#define ATJ_KEY_CTL_REG     KSEG1(ATJ_KEY_BASE + ATJ_KEY_CTL)
#define ATJ_KEY_DAT_REG     KSEG1(ATJ_KEY_BASE + ATJ_KEY_DAT)

#endif /* __ATJ227X_REGS_H__ */
