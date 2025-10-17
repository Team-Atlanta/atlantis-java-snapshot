package org.gts3.atlantis.staticanalysis.utils;

public enum LogLabel {
    LOG_WARN("CRS-JAVA-WARN-static-ana "),
    LOG_ERROR("CRS-JAVA-ERR-static-ana ");

    private final String label;

    LogLabel(String label) {
        this.label = label;
    }

    public String getLabel() {
        return label;
    }

    @Override
    public String toString() {
        return label;
    }
}
