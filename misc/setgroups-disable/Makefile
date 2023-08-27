all: setgroups-disable
setgroups-disable: setgroups-disable.c
	$(CC) -shared -o $@ $<
clean:
	rm -f setgroups-disable
.PHONY: all clean
