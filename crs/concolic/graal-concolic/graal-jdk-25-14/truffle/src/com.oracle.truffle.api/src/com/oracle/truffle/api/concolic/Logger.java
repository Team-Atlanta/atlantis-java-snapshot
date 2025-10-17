package com.oracle.truffle.api.concolic;

import java.util.Map;
import java.util.HashMap;

public class Logger {
    public static final int ALWAYS = -1;
    public static final int INFO = 0;
    public static final int DEBUG = 1;
    public static final int SOLVER_VERBOSE = 2;
    public static final int SOLVER = 3;
    public static final int WARNING = 4;
    public static final int ERROR = 5;

    private static boolean runtimeLogEnabled = false;

    public static boolean compileLog = false;

    private static final Map<String, Integer> LOG_LEVELS = new HashMap<>(
        Map.of(
            "INFO", INFO,
            "DEBUG", DEBUG,
            "SOLVER_VERBOSE", SOLVER_VERBOSE,
            "SOLVER", SOLVER,
            "WARNING", WARNING,
            "ERROR", ERROR,
            "ALWAYS", ALWAYS
        )
    );

    static {
        String logLevelEnv = System.getenv("LOG_LEVEL");
        if (logLevelEnv != null) {
            Integer logLevel = LOG_LEVELS.get(logLevelEnv);
            if (logLevel == Logger.ALWAYS) {
                runtimeLogEnabled = true;
            }
        }
    }


    private static int logLevel = getLogLevel();

    private static int getLogLevel() {
        String logLevelEnv = System.getenv("LOG_LEVEL");
        if (logLevelEnv != null) {
            Integer logLevel = LOG_LEVELS.get(logLevelEnv);
            if (logLevel == null) {
                return Logger.ERROR;
            }
            return logLevel;
        } else {
            return Logger.ERROR;
        }
    }

    public static void enableLogging() {
        runtimeLogEnabled = true;
    }

    public static void disableLogging() {
        runtimeLogEnabled = false;
    }

    public static void INFO(String message) {
        if (runtimeLogEnabled == false) {
            return;
        }
        String prefix = "[INFO]";
        if (logLevel <= INFO) {
            System.out.println(prefix + " " + message);
        }
    }

    public static void DEBUG(String message) {
        if (runtimeLogEnabled == false) {
            return;
        }
        String prefix = "[DEBUG]";
        if (logLevel <= DEBUG) {
            System.out.println(prefix + " " + message);
        }
    }

    public static void SOLVER_VERBOSE(String message) {
        String prefix = "[SOLVER_VERBOSE]";
        if (logLevel <= SOLVER_VERBOSE) {
            System.out.println(prefix + " " + message);
        }
    }

    public static void SOLVER(String message) {
        String prefix = "[SOLVER]";
        if (logLevel <= SOLVER) {
            System.out.println(prefix + " " + message);
        }
    }

    public static void WARNING(String message) {
        if (runtimeLogEnabled == false) {
            return;
        }
        String prefix = "[WARNING]";
        if (logLevel <= WARNING) {
            System.out.println(prefix + " " + message);
        }
    }

    public static void ERROR(String message) {
        if (runtimeLogEnabled == false) {
            return;
        }
        String prefix = "[ERROR]";
        if (logLevel <= ERROR) {
            System.out.println(prefix + " " + message);
        }
    }

    public static void ALWAYS(String message) {
        String prefix = "[ALWAYS]";
        System.out.println(prefix + " " + message);
    }
}
