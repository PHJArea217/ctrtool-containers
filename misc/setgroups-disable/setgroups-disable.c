#include <sys/types.h>
#include <grp.h>
int setgroups(size_t size, const gid_t *gids) {
	return 0;
}
int initgroups(const char *user, gid_t group) {
	return 0;
}
