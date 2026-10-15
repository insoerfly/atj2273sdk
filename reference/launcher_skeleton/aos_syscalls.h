/*
 * AOS (Actions OS) syscall stubs for our device (MP5 X7 / ATJ2273S).
 * Numbers verified against uli/actsemi (257/287 exact matches, see ../syscall_check.txt).
 * ABI:  li $v1, <number> ; syscall 0   (return value in $v0, errno in $a3 per AOS)
 *
 * NOTE: AOS syscall numbers observed in our zapps(*.app) and modules(xxx.bin) are
 * identical to actsemi's table, so this header is the correct API for our firmware.
 */
#ifndef AOS_SYSCALLS_H
#define AOS_SYSCALLS_H

#define SYSCALL(name, no) \
    asm(".global " #name "\n" #name ":\n" "li $v1, " #no "\n" "syscall 0\n");

/* --- core / sync --- */
SYSCALL(os_sched_lock,     0x10002)
SYSCALL(os_sched_unlock,   0x10003)
SYSCALL(mdelay,            0x10035)
SYSCALL(udelay,            0x10036)
SYSCALL(get_count,         0x10038)

/* --- api table registration (IMPORTANT: how a launcher/app exports its API) --- */
SYSCALL(api_install,       0x10028)
SYSCALL(api_uninstall,     0x10029)

/* --- memory --- */
SYSCALL(malloc,            0x1003a)
SYSCALL(free,              0x1003b)
SYSCALL(kmalloc,           0x20023)
SYSCALL(kfree,             0x20024)

/* --- printf/printk --- */
SYSCALL(printf,            0x10032)
SYSCALL(printk,            0x20062)

/* --- low-level fs (module/libc_fs layer) --- */
SYSCALL(sys_open,          0x10044)
SYSCALL(sys_close,         0x10045)
SYSCALL(sys_read,          0x10046)
SYSCALL(sys_write,         0x10047)
SYSCALL(sys_lseek,         0x10048)
SYSCALL(sys_mount,         0x10041)
SYSCALL(sys_umount,        0x10042)

/* --- libc_fs (POSIX-ish) --- */
SYSCALL(open,              0x60000)
SYSCALL(close,             0x60001)
SYSCALL(read,              0x60002)
SYSCALL(write,             0x60003)
SYSCALL(lseek,             0x60004)
SYSCALL(opendir,           0x6002a)
SYSCALL(readdir,           0x6002b)
SYSCALL(closedir,          0x60030)
SYSCALL(fopen,             0x60014)

/* --- dynamic loader (apps are .so loaded at runtime) --- */
SYSCALL(dlopen,            0x1006c)
SYSCALL(dlclose,           0x1006d)
SYSCALL(dlsym,             0x1006e)

/* --- threads/posix --- */
SYSCALL(pthread_create,    0x70060)
SYSCALL(pthread_exit,      0x70061)
SYSCALL(pthread_self,      0x70063)
SYSCALL(sleep,             0x70083)
SYSCALL(usleep,            0x70084)
SYSCALL(clock_gettime,     0x70085)

/* --- applib / message system (THE launcher's core) --- */
SYSCALL(applib_register_app,   0x120034)
SYSCALL(applib_unregister_app, 0x120035)
SYSCALL(applib_init,           0x120036)
SYSCALL(applib_quit,           0x120037)
SYSCALL(get_msg,               0x120038)
SYSCALL(send_sync_msg,         0x120039)
SYSCALL(reply_sync_msg,        0x12003a)
SYSCALL(send_async_msg,        0x12003b)
SYSCALL(broadcast_msg,         0x12003c)
SYSCALL(dispatch_msg,          0x12003d)
SYSCALL(exit_msg_loop,         0x120040)

/* --- app info --- */
SYSCALL(is_app_exist,        0x120002)
SYSCALL(get_app_name,        0x120005)
SYSCALL(app_running_list_get_list, 0x12000a)

/* --- timers --- */
SYSCALL(set_timer,           0x12000f)
SYSCALL(kill_timer,          0x120014)

/* --- GUI resource / style (sty_*) --- */
SYSCALL(sys_get_app_theme_res_dir,     0x120072)
SYSCALL(sys_get_app_string_res_dir,    0x120074)
SYSCALL(sty_open_app_pic_res,          0x12004b)
SYSCALL(sty_open_app_str_res,          0x12004c)
SYSCALL(sty_set_app_scene,             0x12004f)
SYSCALL(sty_get_app_scene,             0x120050)
SYSCALL(sty_set_common_scene,          0x120051)
SYSCALL(sty_get_common_scene,          0x120052)
SYSCALL(sty_get_string,                0x120055)
SYSCALL(sty_draw_string_res,           0x12005b)
SYSCALL(sty_draw_picture_res,          0x120062)
SYSCALL(sty_draw_picregion_res,        0x120063)
SYSCALL(sty_lcd_update,                0x120070)

/* --- widgets (menu / menuview) --- */
SYSCALL(menu_create,       0x130032)
SYSCALL(menu_delete,       0x130033)
SYSCALL(menu_append_item,  0x13003e)
SYSCALL(menu_remove_all_items, 0x130043)
SYSCALL(menuview_create,   0x130048)
SYSCALL(menuview_delete,   0x130049)
SYSCALL(menuview_paint,    0x13004a)
SYSCALL(menuview_proc_gui, 0x13004b)
SYSCALL(menuview_load_style, 0x13004c)
SYSCALL(menuview_set_menu, 0x13004f)

/* --- scene fusion (transitions) --- */
SYSCALL(fusion_set_first_frame, 0x170001)
SYSCALL(fusion_display,         0x170003)

/* --- config --- */
SYSCALL(get_config,        0x110000)
SYSCALL(set_config,        0x110001)

#endif /* AOS_SYSCALLS_H */
