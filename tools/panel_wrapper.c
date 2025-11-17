#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <pwd.h>
#include <time.h>
#include <errno.h>
#include <stdarg.h>

static const char *LOGFILE = "/var/log/panel/panel-wrapper.log";
static const char *AUTODEPLOY = "/opt/panel/scripts/autodeploy.sh";
static const char *MEMWATCH = "/opt/panel/scripts/memwatch.sh";

static void logmsg(const char *fmt, ...) {
    FILE *f = fopen(LOGFILE, "a");
    if (!f) return;
    time_t t = time(NULL);
    struct tm tm;
    localtime_r(&t, &tm);
    char timestr[64];
    strftime(timestr, sizeof(timestr), "%Y-%m-%dT%H:%M:%S%z", &tm);
    fprintf(f, "%s: ", timestr);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    fprintf(f, "\n");
    fclose(f);
}

static int file_owned_by_allowed(const char *path) {
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    // allow owned by panel or root
    struct passwd *pw = getpwnam("panel");
    uid_t panel_uid = (pw ? pw->pw_uid : (uid_t)-1);
    if (st.st_uid == 0 || st.st_uid == panel_uid) return 1;
    return 0;
}

static int is_valid_url(const char *u) {
    if (!u) return 0;
    if (strlen(u) > 2048) return 0;
    if (strncmp(u, "http://", 7) == 0) return 1;
    if (strncmp(u, "https://", 8) == 0) return 1;
    return 0;
}

static int is_safe_path(const char *p) {
    if (!p) return 0;
    if (strlen(p) > 4096) return 0;
    if (p[0] != '/') return 0;
    // allow under /var/run or /var/tmp or /tmp
    if (strncmp(p, "/var/run/", 9) == 0) return 1;
    if (strncmp(p, "/var/tmp/", 9) == 0) return 1;
    if (strncmp(p, "/tmp/", 5) == 0) return 1;
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <autodeploy|memwatch> [arg]\n", argv[0]);
        return 2;
    }
    const char *cmd = argv[1];
    const char *arg = (argc >= 3 ? argv[2] : NULL);

    uid_t euid = geteuid();
    uid_t uid = getuid();
    gid_t gid = getgid();

    logmsg("invoked by uid=%d euid=%d gid=%d cmd=%s arg=%s", uid, euid, gid, cmd, arg?arg:"(none)");

    const char *script = NULL;
    char *const envp_default[] = { "PATH=/usr/bin:/bin", "LANG=C", NULL };

    if (strcmp(cmd, "autodeploy") == 0) {
        script = AUTODEPLOY;
        if (arg && !is_valid_url(arg)) {
            logmsg("invalid download URL: %s", arg);
            fprintf(stderr, "Invalid URL\n");
            return 3;
        }
    } else if (strcmp(cmd, "memwatch") == 0) {
        script = MEMWATCH;
        if (arg && !is_safe_path(arg)) {
            logmsg("invalid pid file path: %s", arg);
            fprintf(stderr, "Invalid pid file path\n");
            return 3;
        }
    } else {
        logmsg("unknown command: %s", cmd);
        fprintf(stderr, "Unknown command\n");
        return 2;
    }

    // Ensure script exists and is executable and owned by allowed user
    if (access(script, X_OK) != 0) {
        logmsg("script not executable: %s (errno=%d)", script, errno);
        fprintf(stderr, "Script not executable\n");
        return 4;
    }
    if (!file_owned_by_allowed(script)) {
        logmsg("script not owned by panel or root: %s", script);
        fprintf(stderr, "Script ownership invalid\n");
        return 5;
    }

    // Prepare sanitized environment
    char **envp = NULL;
    if (strcmp(cmd, "autodeploy") == 0) {
        if (arg) {
            // set DOWNLOAD_URL
            size_t len = strlen("DOWNLOAD_URL=") + strlen(arg) + 1;
            char *e = malloc(len);
            if (!e) return 10;
            snprintf(e, len, "DOWNLOAD_URL=%s", arg);
            envp = malloc(sizeof(char*) * 4);
            envp[0] = e;
            envp[1] = strdup("PATH=/usr/bin:/bin");
            envp[2] = strdup("LANG=C");
            envp[3] = NULL;
        } else {
            envp = envp_default;
        }
    } else { // memwatch
        if (arg) {
            size_t len = strlen("ET_PID_FILE=") + strlen(arg) + 1;
            char *e = malloc(len);
            if (!e) return 10;
            snprintf(e, len, "ET_PID_FILE=%s", arg);
            envp = malloc(sizeof(char*) * 4);
            envp[0] = e;
            envp[1] = strdup("PATH=/usr/bin:/bin");
            envp[2] = strdup("LANG=C");
            envp[3] = NULL;
        } else {
            envp = envp_default;
        }
    }

    // Execute the script with sanitized environment
    char *const exec_args[] = { (char*)script, NULL };
    logmsg("executing %s", script);
    if (execve(script, exec_args, envp) == -1) {
        logmsg("execve failed: %d", errno);
        perror("execve");
        return 6;
    }

    return 0;
}
