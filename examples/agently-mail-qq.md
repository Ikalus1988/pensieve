---
id: agently-mail-qq
title: Agently mail/QQ inbox routine
type: routine
status: active
confidence: verified
aliases:
  - agently cli
  - agently mail
  - 邮件收发
  - 查收邮件
  - 收件箱
  - support@glama.ai
  - Glama Discord
trigger_phrases:
  - 检查邮件收发记忆
  - 查收邮件
  - 代发邮件
  - 发 support 邮件
  - 通过 agently cli 发邮件
  - 不要坚持己见
cwd_hints:
  - C:\Users\hp
checklist:
  - identify whether the task is email sending or inbox checking
  - search the mail routine before arguing about tool capability
  - confirm the concrete address or channel
  - use the mail cli workflow if available
  - verify delivery or read status
deliverables:
  - sent email or inbox result
  - confirmation evidence
tags:
  - agently
  - mail
  - qq
  - glama
source_sessions:
  - local support case
---
# Agently mail / QQ inbox routine

## When to use

Use when the user asks to send, check, forward, or search mail, or when they mention Agently CLI, QQ mail, support@glama.ai, or Glama Discord.

## Checklist

1. Search the mail routine first.
2. Treat tool-name mentions and mailbox/channel names as strong recall cues.
3. If the user is correcting you, prefer recall over arguing about tool capability.
4. Confirm the exact recipient or channel.
5. Execute the mail workflow and verify the result.
