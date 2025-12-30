---
labels:
- Stage-Alpha
summary: Install adhoc command bots in MUCs
---

# Introduction

This module allows you to "install" bots on a MUC service (via config for
now, via adhoc command and on just one MUC to follow). All the adhoc commands
defined on the bot become adhoc commands on the service's MUCs, and the bots
can send XEP-0356 messages to the MUC to send messages as any participant.

# Configuration

List all bots to install. You must specify full JID.

    adhoc_bots = { "some@bot.example.com/bot" }
	
And enable the module on the MUC service as usual

    modules_enabled = { "muc_adhoc_bots" }
