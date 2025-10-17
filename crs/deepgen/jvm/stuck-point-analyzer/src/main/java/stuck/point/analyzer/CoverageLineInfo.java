package stuck.point.analyzer;

import java.util.Objects;

/**
 * Represents a line with coverage information from JaCoCo analysis.
 * This is the tuple format: <class FQN, java file name, line number>
 */
public class CoverageLineInfo {
    
    private final String classFqn;
    private final String fileName;
    private final int lineNumber;
    private final String coverageStatus;
    private final int instructionsTotal;
    private final int instructionsCovered;
    private final int branchesTotal;
    private final int branchesCovered;
    
    public CoverageLineInfo(String classFqn, String fileName, int lineNumber, 
                           String coverageStatus, int instructionsTotal, int instructionsCovered,
                           int branchesTotal, int branchesCovered) {
        this.classFqn = classFqn;
        this.fileName = fileName;
        this.lineNumber = lineNumber;
        this.coverageStatus = coverageStatus;
        this.instructionsTotal = instructionsTotal;
        this.instructionsCovered = instructionsCovered;
        this.branchesTotal = branchesTotal;
        this.branchesCovered = branchesCovered;
    }
    
    public String getClassFqn() {
        return classFqn;
    }
    
    public String getFileName() {
        return fileName;
    }
    
    public int getLineNumber() {
        return lineNumber;
    }
    
    public String getCoverageStatus() {
        return coverageStatus;
    }
    
    public int getInstructionsTotal() {
        return instructionsTotal;
    }
    
    public int getInstructionsCovered() {
        return instructionsCovered;
    }
    
    public int getBranchesTotal() {
        return branchesTotal;
    }
    
    public int getBranchesCovered() {
        return branchesCovered;
    }
    
    /**
     * Returns true if this line has partial coverage (some but not all instructions covered)
     */
    public boolean isPartlyCovered() {
        return "PARTLY_COVERED".equals(coverageStatus);
    }
    
    /**
     * Returns true if this line is not covered at all
     */
    public boolean isNotCovered() {
        return "NOT_COVERED".equals(coverageStatus);
    }
    
    /**
     * Returns true if this line is fully covered
     */
    public boolean isFullyCovered() {
        return "FULLY_COVERED".equals(coverageStatus);
    }
    
    /**
     * Get coverage ratio for instructions (0.0 to 1.0)
     */
    public double getInstructionCoverageRatio() {
        if (instructionsTotal == 0) return 0.0;
        return (double) instructionsCovered / instructionsTotal;
    }
    
    /**
     * Get coverage ratio for branches (0.0 to 1.0)
     */
    public double getBranchCoverageRatio() {
        if (branchesTotal == 0) return 0.0;
        return (double) branchesCovered / branchesTotal;
    }
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        CoverageLineInfo that = (CoverageLineInfo) o;
        return lineNumber == that.lineNumber &&
               Objects.equals(classFqn, that.classFqn) &&
               Objects.equals(fileName, that.fileName);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(classFqn, fileName, lineNumber);
    }
    
    @Override
    public String toString() {
        return String.format("%s | %s | %d | %s (inst: %d/%d, branches: %d/%d)",
                classFqn, fileName, lineNumber, coverageStatus,
                instructionsCovered, instructionsTotal,
                branchesCovered, branchesTotal);
    }
}