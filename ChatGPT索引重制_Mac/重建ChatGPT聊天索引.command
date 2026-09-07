#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
/usr/bin/python3 ./rebuild_chatgpt_index.py
result=$?
printf '\n按回车关闭此窗口。'
read -r _chatgpt_rebuild_done
exit "$result"
