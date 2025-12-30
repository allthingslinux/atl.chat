---
labels:
- 'Stage-Alpha'
summary: 'Measure number of daily, weekly and monthly active users'
...

Introduction
============

This module calculates the number of daily, weekly and monthly active users -
often abbreviated as DAU, WAU and MAU.

These metrics are more accurate for determining how many people are actually
using a service. For example simply counting registered accounts will typically
include many dormant accounts that aren't really being used. Many servers also
track the number of connected users. This is a useful metric for many purposes,
but it is generally lower than the actual number of users - because some users
may only connect at certain times of day.

The module defines "activity" as any login/logout event during the time period,
and for this it depends on mod_lastlog2 being loaded (it reads the data stored
by mod_lastlog2). Each individual user is only counted once.

"Daily" means any event within the past 24 hours, "weekly" means within the
past 7 days, and "monthly" means within the past 30 days.

Details
=======

The user count is calculated shortly after startup, and then recalculated
hourly after that.

Metrics are exported using Prosody's built-in statistics API.

There is no configuration for this module.

Compatibility
=============

Requires Prosody 0.11 or later with mod_lastlog2 enabled.
