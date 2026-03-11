/* Copyright (C) 2023 Valentin Lorentz (original)
 * Copyright (C) 2025 atl.chat (redact-atl fixes)
 * License: GPLv3
 *
 * atl.chat redact-atl: fixed REDACT implementation.
 * - parc/parv[2] validation before strdup (prevents segfault)
 * - Correct config test logic for set::redacters
 * - Correct ERR_NEEDMOREPARAMS command name
 *
 * Based on unrealircd-contrib third/redact. Uses third/redact-atl to avoid
 * collision with upstream during build.
 */
/*** <<<MODULE MANAGER START>>>
module
{
        documentation "https://github.com/ircv3/ircv3-specifications/pull/524";
        troubleshooting "In case of problems, contact val on
irc.unrealircd.org."; min-unrealircd-version "6.1.2"; post-install-text { "The
module is installed. Add to unrealircd.conf:"; "loadmodule
\"third/redact-atl\";"; "And /REHASH the IRCd.";
        }
}
*** <<<MODULE MANAGER END>>>
*/

#include "unrealircd.h"

CMD_FUNC(cmd_redact);

long CAP_MESSAGE_REDACTION = 0L;
bool sender_can_redact = 0;
char *chan_access_pattern = "";

int redact_config_run(ConfigFile *cf, ConfigEntry *ce, int type);
int redact_config_test(ConfigFile *cf, ConfigEntry *ce, int type, int *errs);

ModuleHeader MOD_HEADER = {
    "third/redact-atl",
    "6.0.1",
    "IRCv3 message-redaction (atl.chat: fixed)",
    "atl.chat",
    "unrealircd-6",
};

MOD_INIT() {
  ClientCapabilityInfo c;

  chan_access_pattern = "";
  sender_can_redact = 0;

  CommandAdd(modinfo->handle, "REDACT", cmd_redact, MAXPARA,
             CMD_USER | CMD_SERVER);
  HookAdd(modinfo->handle, HOOKTYPE_CONFIGRUN, 0, redact_config_run);

  memset(&c, 0, sizeof(c));
  c.name = "draft/message-redaction";
  ClientCapabilityAdd(modinfo->handle, &c, &CAP_MESSAGE_REDACTION);
  return MOD_SUCCESS;
}

MOD_LOAD() {
  HookAdd(modinfo->handle, HOOKTYPE_CONFIGRUN, 0, redact_config_run);
  return MOD_SUCCESS;
}

MOD_UNLOAD() { return MOD_SUCCESS; }

MOD_TEST() {
  HookAdd(modinfo->handle, HOOKTYPE_CONFIGTEST, 0, redact_config_test);
  return MOD_SUCCESS;
}

int redact_config_run(ConfigFile *cf, ConfigEntry *ce, int type) {
  ConfigEntry *cep;
  bool owners_can_redact = 0, admins_can_redact = 0, ops_can_redact = 0,
       halfops_can_redact = 0;

  if (type != CONFIG_SET)
    return 0;
  if (!ce || !ce->name || strcmp(ce->name, "redacters"))
    return 0;

  sender_can_redact = 0;
  for (cep = ce->items; cep; cep = cep->next) {
    if (!cep->name)
      continue;
    if (!strcmp(cep->name, "owner"))
      owners_can_redact = 1;
    else if (!strcmp(cep->name, "admin"))
      admins_can_redact = 1;
    else if (!strcmp(cep->name, "op"))
      ops_can_redact = 1;
    else if (!strcmp(cep->name, "halfop"))
      halfops_can_redact = 1;
    else if (!strcmp(cep->name, "sender"))
      sender_can_redact = 1;
  }

  if (halfops_can_redact)
    chan_access_pattern = "hoaq";
  else if (ops_can_redact)
    chan_access_pattern = "oaq";
  else if (admins_can_redact)
    chan_access_pattern = "aq";
  else if (owners_can_redact)
    chan_access_pattern = "q";
  else
    chan_access_pattern = "";

  return 1;
}

int redact_config_test(ConfigFile *cf, ConfigEntry *ce, int type, int *errs) {
  int errors = 0;
  ConfigEntry *cep;

  if (type != CONFIG_SET)
    return 0;
  if (!ce || !ce->name || strcmp(ce->name, "redacters"))
    return 0;

  for (cep = ce->items; cep; cep = cep->next) {
    if (!cep->name) {
      config_error("%s:%i: blank set::redacters item", cep->file->filename,
                   cep->line_number);
      errors++;
      continue;
    }
    if (strcmp(cep->name, "owner") && strcmp(cep->name, "admin") &&
        strcmp(cep->name, "op") && strcmp(cep->name, "halfop") &&
        strcmp(cep->name, "sender")) {
      config_error("%s:%i: invalid set::redacters item: %s",
                   cep->file->filename, cep->line_number, cep->name);
      errors++;
    }
  }

  *errs = errors;
  return errors ? -1 : 1;
}

CMD_FUNC(cmd_redact) {
  HistoryFilter *filter = NULL;
  Channel *channel;
  const char *error = NULL;
  int deleted, rejected_deletes;

  if ((parc < 3) || BadPtr(parv[1]) || BadPtr(parv[2])) {
    sendnumeric(client, ERR_NEEDMOREPARAMS, "REDACT");
    return;
  }

  channel = find_channel(parv[1]);
  if (!channel) {
    sendto_one(
        client, NULL,
        ":%s FAIL REDACT INVALID_TARGET %s :Chat history is not enabled in PM",
        me.name, parv[1]);
    return;
  }

  if (ValidatePermissionsForPath("chat:redact", client, NULL, NULL, NULL)) {
    /* Oper: allow */
  } else if (MyUser(client) &&
             (!BadPtr(chan_access_pattern) &&
              check_channel_access(client, channel, chan_access_pattern))) {
    /* Chanop: allow */
  } else if (sender_can_redact) {
    /* Will check sender after we fetch the message */
  } else {
    error = "sender can't redact, and neither oper nor chanop";
    goto unauthorized;
  }

  filter = safe_alloc(sizeof(HistoryFilter));
  filter->cmd = HFC_AROUND;
  filter->msgid_a = strdup(parv[2]);
  filter->limit = 1;

  if (sender_can_redact && MyUser(client) &&
      !ValidatePermissionsForPath("chat:redact", client, NULL, NULL, NULL) &&
      (BadPtr(chan_access_pattern) ||
       !check_channel_access(client, channel, chan_access_pattern))) {
    if (IsLoggedIn(client))
      filter->account = strdup(client->user->account);
    else {
      error = "neither oper/chanop nor logged in";
      goto unauthorized;
    }
  }

  deleted = history_delete(channel->name, filter, &rejected_deletes);

  if (deleted > 1) {
    sendto_one(client, NULL,
               ":%s FAIL REDACT UNKNOWN_ERROR %s :history_delete found more "
               "than one result",
               me.name, parv[1]);
    goto end;
  }
  if (rejected_deletes > 1) {
    sendto_one(client, NULL,
               ":%s FAIL REDACT UNKNOWN_ERROR %s :history_delete rejected more "
               "than one result",
               me.name, parv[1]);
    goto end;
  }
  if (deleted && rejected_deletes) {
    sendto_one(client, NULL,
               ":%s FAIL REDACT UNKNOWN_ERROR %s %s :history_delete both "
               "deleted and rejected",
               me.name, parv[1], parv[2]);
    goto end;
  }
  if (rejected_deletes) {
    error = "not sender";
    goto unauthorized;
  }
  if (!deleted) {
    sendto_one(client, NULL,
               ":%s FAIL REDACT UNKNOWN_MSGID %s %s :This message does not "
               "exist or is too old",
               me.name, parv[1], parv[2]);
    goto end;
  }

  if (parc >= 4) {
    sendto_channel(channel, client, NULL, NULL, CAP_MESSAGE_REDACTION, SEND_ALL,
                   NULL, ":%s REDACT %s %s :%s", client->name, parv[1], parv[2],
                   parv[3]);
  } else {
    sendto_channel(channel, client, NULL, NULL, CAP_MESSAGE_REDACTION, SEND_ALL,
                   NULL, ":%s REDACT %s %s", client->name, parv[1], parv[2]);
  }
  goto end;

unauthorized:
  sendto_one(client, NULL,
             ":%s FAIL REDACT REDACT_FORBIDDEN %s %s :You are not authorized "
             "to redact messages in %s: %s",
             me.name, parv[1], parv[2], parv[1], error);
end:
  if (filter)
    free_history_filter(filter);
}
