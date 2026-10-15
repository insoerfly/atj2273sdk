/*
 * launcher.c — skeleton of a custom launcher for MP5 X7 (ATJ2273S, Actions AOS).
 *
 * Model copied from uli/actsemi (verified API) + our firmware modules
 * (desktop/launcher: desktop_parse, scene_desktop_t, menuview_*, sty_*, applib_*).
 *
 * This file is a STRUCTURAL skeleton: syscall names/numbers are correct for our
 * device (see aos_syscalls.h), but some function prototypes are still TODO and
 * must be confirmed against the real modules (119/123/124) by disassembly.
 *
 * Build: see Makefile (mipsel-sde-elf-gcc) + actsemi.ld (set base to fit how the
 * OS loads it — our apps use 0x65800000, desktop modules ~0x47c00000).
 */
#include "aos_syscalls.h"
#include <string.h>

#define VERSION  "tlauncher R0.1"

/* ---- app registration table (exported for the OS) -------------------------
 * The OS/desktop discovers the launcher by "api_install(id, table)".
 * actsemi uses id 7 for the P1(PS1) plugin; our desktop id is TBD — check
 * modules 119/123/124 (desktop_parse) to find the id used for the launcher. */
#define LAUNCHER_API_ID   2            /* TODO: confirm against real desktop */

typedef struct {
    int  (*loop)(void);                /* called each frame */
    void (*enqueue_key)(void *ev);     /* raw key event */
    int  (*control)(int cmd, void *d); /* control (init/name/keys/shutdown...) */
} launcher_api_t;

static int  launcher_loop(void);
static void launcher_enqueue_key(void *ev);
static int  launcher_control(int cmd, void *data);

static launcher_api_t g_api = { launcher_loop, launcher_enqueue_key, launcher_control };

/* ---- scene / menu state --------------------------------------------------- */
struct app_entry {
    char     name[64];
    char     path[256];                /* path to the .app/.so to dlopen */
};

#define MAX_APPS 64
static struct app_entry g_apps[MAX_APPS];
static int  g_app_count;
static void *g_cur_scene;              /* from sty_get_common_scene()/load_scene */
static void *g_cur_menu;               /* menu_create() result */

/* ---- helpers -------------------------------------------------------------- */
/* Parse "[Desktop Entry]" files under /mnt/diska/apps (format confirmed in
 * module 124):  Path=..., Type=Application, Exec=..., Icon=..., Name=...      */
static int scan_apps(const char *dir)
{
    /* TODO: opendir/readdir(dir); for each *.desktop read & parse; fill g_apps */
    (void)dir;
    g_app_count = 0;
    return g_app_count;
}

/* Launch an app: unload launcher UI, dlopen the app, hand over control. */
static int launch_app(struct app_entry *e)
{
    void *h;
    int (*fn)(void);

    /* try: real app = ELF (.app) that exports "api_table" (see actsemi) */
    h = dlopen(e->path, 2);
    if (!h) return -1;
    fn = (int (*)(void))dlsym(h, "api_table");
    if (!fn) return -1;
    /* TODO: on our SoC the loader entry may differ (entry field / .init proc). */
    return 0;
}

/* ---- launcher API (what the OS calls) ------------------------------------ */
static int launcher_loop(void)
{
    /* one frame: process messages, paint the menu */
    menuview_paint(g_cur_menu);
    sty_lcd_update();
    return 0;
}

static void launcher_enqueue_key(void *ev)
{
    /* translate raw key -> menu navigation; TODO: real keymap (KEY_*.TXT) */
    menuview_proc_gui(g_cur_menu);
    (void)ev;
}

static int launcher_control(int cmd, void *data)
{
    switch (cmd) {
    case 0:                             /* init */
        sty_set_common_scene(g_cur_scene);
        scan_apps("/mnt/diska/apps");
        g_cur_menu = menu_create();
        for (int i = 0; i < g_app_count; i++)
            menu_append_item(g_cur_menu, g_apps[i].name);   /* TODO: real sig */
        menuview_set_menu(g_cur_menu);
        return 0;
    case 2:                             /* app/name selected -> launch */
        for (int i = 0; i < g_app_count; i++)
            if (!strcmp(g_apps[i].name, (char *)data))
                return launch_app(&g_apps[i]);
        return -1;
    case 3:                             /* shutdown */
        return 0;
    default:
        return 0;
    }
}

/* ---- entry points --------------------------------------------------------- */
/* The OS/module loader jumps to a section-entered init; actsemi uses ".init". */
void __attribute__((section(".init"))) _init_proc(void)
{
    api_install(LAUNCHER_API_ID, (void **)&g_api);
}

void __attribute__((section(".fini"))) _term_proc(void)
{
    api_uninstall(LAUNCHER_API_ID);
}

char *TLAUNCHER_VERSION = VERSION;
