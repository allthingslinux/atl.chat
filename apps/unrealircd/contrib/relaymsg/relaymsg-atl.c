/* Copyright © 2025 Valware
 * License: GPLv3
 * Name: third/relaymsg-atl (atl.chat fork)
 *
 * Modified by atl.chat: add require-separator config option to allow clean nicks
 * (no / suffix) for cross-platform name consistency. Default: yes (upstream behavior).
 *
 * Uses unique name third/relaymsg-atl to avoid collision with upstream third/relaymsg
 * during UnrealIRCd build (make runs "unrealircd -m upgrade" which overwrites contrib modules).
 */
/*** <<<MODULE MANAGER START>>>
module
{
	documentation "https://github.com/ValwareIRC/valware-unrealircd-mods/blob/main/relaymsg/README.md";
	troubleshooting "In case of problems, check the documentation or e-mail me at v.a.pond@outlook.com";
	min-unrealircd-version "6.1.0";
	max-unrealircd-version "6.*";
	post-install-text {
		"The module is installed. Add to unrealircd.conf:";
		"loadmodule \"third/relaymsg-atl\";";
		"Then: ./unrealircd rehash";
	}
}
*** <<<MODULE MANAGER END>>>
*/

#include "unrealircd.h"

#define CONF_BLOCK_NAME "relaymsg"
#define NAME_RELAYMSG "draft/relaymsg"

long CAP_RELAYMSG = 0L;

void set_config(void);
void free_config(void);
int hookfunc_configtest(ConfigFile *cf, ConfigEntry *ce, int type, int *errs);
int hookfunc_configrun(ConfigFile *cf, ConfigEntry *ce, int type);

/** Returns 1 if cep->name is a separator/clean-nicks option (hyphen or underscore). */
static int is_separator_option(const char *name)
{
	if (!name)
		return 0;
	return !strcmp(name, "allow-clean-nicks") || !strcmp(name, "allow_clean_nicks") ||
	       !strcmp(name, "require-separator") || !strcmp(name, "require_separator");
}

int relaymsg_tag_is_ok(Client *client, const char *name, const char *value);
const char *relay_msg_cap_parameter(Client *client);

CMD_FUNC(cmd_relaymsg);
CMD_FUNC(cmd_rrelaymsg);

struct MyConfStruct
{
	char *hostmask;
	bool got_hostmask;
	bool require_separator;
};
static struct MyConfStruct MyConf;

ModuleHeader MOD_HEADER = {
	"third/relaymsg-atl",
	"1.0.1",
	"Implements draft/relaymsg (atl.chat: optional separator)",
	"Valware",
	"unrealircd-6",
};

MOD_INIT()
{
	ClientCapabilityInfo c;
	ClientCapability *c2;
	MessageTagHandlerInfo mtag;

	MARK_AS_GLOBAL_MODULE(modinfo);

	set_config();
	HookAdd(modinfo->handle, HOOKTYPE_CONFIGRUN, 0, hookfunc_configrun);

	memset(&c, 0, sizeof(c));
	c.name = NAME_RELAYMSG;
	c.parameter = relay_msg_cap_parameter;
	c2 = ClientCapabilityAdd(modinfo->handle, &c, &CAP_RELAYMSG);

	memset(&mtag, 0, sizeof(mtag));
	mtag.name = NAME_RELAYMSG;
	mtag.is_ok = relaymsg_tag_is_ok;
	mtag.clicap_handler = c2;
	MessageTagHandlerAdd(modinfo->handle, &mtag);

	CommandAdd(modinfo->handle, "RELAYMSG", cmd_relaymsg, 4, CMD_USER|CMD_SERVER|CMD_NOLAG);
	CommandAdd(modinfo->handle, "RRELAYMSG", cmd_rrelaymsg, 5, CMD_SERVER|CMD_NOLAG|CMD_BIGLINES);

	return MOD_SUCCESS;
}

MOD_LOAD()
{
	return MOD_SUCCESS;
}

MOD_UNLOAD()
{
	free_config();
	return MOD_SUCCESS;
}

MOD_TEST()
{
	memset(&MyConf, 0, sizeof(MyConf));
	HookAdd(modinfo->handle, HOOKTYPE_CONFIGTEST, 0, hookfunc_configtest);
	return MOD_SUCCESS;
}

void set_config(void)
{
	safe_strdup(MyConf.hostmask, "unreal@localhost");
	MyConf.require_separator = 1; /* default: yes, upstream behavior */
}

void free_config(void)
{
	safe_free(MyConf.hostmask);
}

int hookfunc_configtest(ConfigFile *cf, ConfigEntry *ce, int type, int *errs)
{
	int errors = 0;
	ConfigEntry *cep;

	if (type != CONFIG_MAIN)
		return 0;
	if (!ce || !ce->name)
		return 0;
	if (strcmp(ce->name, CONF_BLOCK_NAME))
		return 0;

	for (cep = ce->items; cep; cep = cep->next)
	{
		if (is_separator_option(cep->name))
		{
			if (!cep->value || !*cep->value)
			{
				config_error("%s:%i: %s::allow-clean-nicks requires yes or no", cep->file->filename, cep->line_number, CONF_BLOCK_NAME);
				errors++;
			}
			else if (!strcasecmp(cep->value, "yes") || !strcasecmp(cep->value, "true") || !strcmp(cep->value, "1"))
				; /* ok */
			else if (!strcasecmp(cep->value, "no") || !strcasecmp(cep->value, "false") || !strcmp(cep->value, "0"))
				; /* ok */
			else
			{
				config_error("%s:%i: %s::allow-clean-nicks must be yes or no", cep->file->filename, cep->line_number, CONF_BLOCK_NAME);
				errors++;
			}
			continue;
		}

		if (!cep->value)
		{
			config_error("%s:%i: blank %s value", cep->file->filename, cep->line_number, CONF_BLOCK_NAME);
			errors++;
			continue;
		}

		if (!strcmp(cep->name, "hostmask"))
		{
			if (MyConf.got_hostmask)
			{
				config_error("%s:%i: duplicate %s::%s directive", cep->file->filename, cep->line_number, CONF_BLOCK_NAME, cep->name);
				errors++;
				continue;
			}
			MyConf.got_hostmask = 1;
			if (!strlen(cep->value) || !strcmp(cep->value, "@"))
			{
				config_error("%s:%i: %s::%s must be non-empty and be in nick@hostmask format", cep->file->filename, cep->line_number, CONF_BLOCK_NAME, cep->name);
				errors++;
			}
			if (!strchr(cep->value, '@'))
			{
				config_error("%s:%i: %s::%s must be in nick@hostmask format", cep->file->filename, cep->line_number, CONF_BLOCK_NAME, cep->name);
				errors++;
			}
			continue;
		}

		config_warn("%s:%i: unknown item %s::%s", cep->file->filename, cep->line_number, CONF_BLOCK_NAME, cep->name);
	}

	*errs = errors;
	return errors ? -1 : 1;
}

int hookfunc_configrun(ConfigFile *cf, ConfigEntry *ce, int type)
{
	ConfigEntry *cep;

	if (type != CONFIG_MAIN)
		return 0;
	if (!ce || !ce->name)
		return 0;
	if (strcmp(ce->name, CONF_BLOCK_NAME))
		return 0;

	for (cep = ce->items; cep; cep = cep->next)
	{
		if (!cep->name)
			continue;

		if (!strcmp(cep->name, "hostmask"))
		{
			safe_strdup(MyConf.hostmask, cep->value);
			continue;
		}
		if (is_separator_option(cep->name))
		{
			int yes_val = cep->value && (!strcasecmp(cep->value, "yes") || !strcasecmp(cep->value, "true") || !strcmp(cep->value, "1"));
			/* allow-clean-nicks yes => require_separator no; require-separator yes => require_separator yes */
			if (!strcmp(cep->name, "allow-clean-nicks") || !strcmp(cep->name, "allow_clean_nicks"))
				MyConf.require_separator = !yes_val;  /* allow-clean-nicks yes = no separator required */
			else
				MyConf.require_separator = yes_val;   /* require-separator yes = separator required */
			continue;
		}
	}

	return 1;
}

int relaymsg_tag_is_ok(Client *client, const char *name, const char *value)
{
	if (IsServer(client))
		return 1;
	return 0;
}

const char *relay_msg_cap_parameter(Client *client)
{
	return "/";
}

static int nick_has_valid_separator(const char *nick)
{
	if (!MyConf.require_separator)
		return 1;
	return strchr(nick, '/') != NULL;
}

CMD_FUNC(cmd_relaymsg)
{
	MessageTag *mtags = NULL, *m = NULL;

	if (!HasCapability(client, NAME_RELAYMSG))
		return;

	if (!ValidatePermissionsForPath("relaymsg", client, NULL, NULL, NULL))
	{
		sendnumeric(client, ERR_NOPRIVILEGES);
		return;
	}

	if (parc < 3)
	{
		sendnumeric(client, ERR_NEEDMOREPARAMS, "RELAYMSG");
		return;
	}

	{
		const char *invalid_chars = " \t\n\r!+%@&#$:'\"?*,.";
		for (const char *p = parv[2]; *p; p++)
		{
			if (strchr(invalid_chars, *p))
			{
				sendnotice(client, "Invalid characters in spoofed nick");
				return;
			}
		}
	}

	if (!nick_has_valid_separator(parv[2]))
	{
		sendnotice(client, "Invalid spoofed nick format (require-separator is yes; nick must contain /)");
		return;
	}

	if (strlen(parv[2]) > 35)
	{
		sendnotice(client, "Spoofed nick too long");
		return;
	}

	{
		Channel *channel = find_channel(parv[1]);
		if (!channel)
		{
			sendnumeric(client, ERR_NOSUCHCHANNEL, parv[1]);
			return;
		}

		sendnotice(client, "Sending message to %s", parv[1]);

		m = safe_alloc(sizeof(MessageTag));
		safe_strdup(m->name, NAME_RELAYMSG);
		safe_strdup(m->value, client->name);
		AddListItem(m, mtags);
		new_message(client, recv_mtags, &mtags);

		sendto_channel(channel, &me, NULL, NULL, 0, SEND_LOCAL, mtags,
			":%s!%s PRIVMSG %s :%s", parv[2], MyConf.hostmask, parv[1], parv[3]);
		sendto_server(NULL, 0, 0, mtags,
			":%s RRELAYMSG %s %s %s :%s", me.name, client->id, parv[1], parv[2], parv[3]);
	}
}

CMD_FUNC(cmd_rrelaymsg)
{
	if (parc < 5)
		return;

	/* parv[1]=client_id, parv[2]=channel, parv[3]=spoofed_nick, parv[4]=message */
	{
		const char *invalid_chars = " \t\n\r!+%@&#$:'\"?*,.";
		for (const char *p = parv[3]; *p; p++)
			if (strchr(invalid_chars, *p))
				return;

		if (!nick_has_valid_separator(parv[3]))
			return;
	}

	{
		Channel *channel = find_channel(parv[2]);
		if (!channel)
			return;

		sendto_channel(channel, &me, NULL, NULL, 0, SEND_LOCAL, recv_mtags,
			":%s!%s PRIVMSG %s :%s", parv[3], MyConf.hostmask, parv[2], parv[4]);
		sendto_server(client, 0, 0, recv_mtags,
			":%s RRELAYMSG %s %s %s :%s", me.name, parv[1], parv[2], parv[3], parv[4]);
	}
}
