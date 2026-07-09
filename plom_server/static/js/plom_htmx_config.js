/*
    SPDX-License-Identifier: AGPL-3.0-or-later
    Copyright (C) 2026 Aidan Murphy
*/
/* global htmx */

// response-targets changes event.detail.successful
// to true on error responses (!!!)
// see "Configure" in the response-targets docs:
// https://htmx.org/extensions/response-targets/
htmx.config.responseTargetUnsetsError = false;
