#include <linux/init.h>
#include <linux/module.h>

static int __init scr_approx_abi_probe_init(void)
{
	pr_info("SCR REQ-0001 approximate ABI probe: init\n");
	return 0;
}

static void __exit scr_approx_abi_probe_exit(void)
{
	pr_info("SCR REQ-0001 approximate ABI probe: exit\n");
}

module_init(scr_approx_abi_probe_init);
module_exit(scr_approx_abi_probe_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("SCR SDLC diagnostic probe");
MODULE_DESCRIPTION("DIAGNOSTIC APPROXIMATE ABI - NOT PRODUCTION");
