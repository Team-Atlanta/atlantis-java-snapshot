package com.oracle.truffle.api.concolic;

public class Config {

    private static Config instance;

    private boolean solverDebug;
    private boolean timeoutInterrupted;

    static boolean getBooleanEnv(String envName, boolean defaultValue) {
        String targetEnvValue = System.getenv(envName);
        if (targetEnvValue == null || targetEnvValue.length() == 0) {
            return defaultValue;
        } else {
            if (targetEnvValue.equals("1") || targetEnvValue.equals("true")) {
                return true;
            } else {
                return false;
            }
        }
    }
    static {
        instance = null;
    }

    private Config() {
        solverDebug = getBooleanEnv("SOLVER_DEBUG", false);
        timeoutInterrupted = false;
    }

    public void resetTimeoutInterrupted() {
        timeoutInterrupted = false;
    }

    public void setTimeoutInterrupted() {
        timeoutInterrupted = true;
    }

    public boolean getTimeoutInterrupted() {
        return timeoutInterrupted;
    }

    public static Config getInstance() {
        if (instance == null) {
            instance = new Config();
        }
        return instance;
    }

    public boolean getSolverDebug() {
        return this.solverDebug;
    }

}
