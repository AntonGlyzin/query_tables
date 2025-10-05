dir /s /b ..\*.py > files.txt
xgettext -d query_tables -o ./en/LC_MESSAGES/query_tables.po --files-from=files.txt --from-code=UTF-8 -j
del files.txt