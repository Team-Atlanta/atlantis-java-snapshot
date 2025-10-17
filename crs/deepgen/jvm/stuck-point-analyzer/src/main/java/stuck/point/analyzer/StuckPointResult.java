package stuck.point.analyzer;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Represents the result of stuck point analysis for a single line.
 * Contains both coverage information and calculated score.
 */
public class StuckPointResult {
    
    @JsonProperty("classFqn")
    private final String classFqn;
    
    @JsonProperty("fileName")
    private final String fileName;
    
    @JsonProperty("lineNumber")
    private final int lineNumber;
    
    @JsonProperty("coverageStatus")
    private final String coverageStatus;
    
    @JsonProperty("instructionCoverage")
    private final CoverageStats instructionCoverage;
    
    @JsonProperty("branchCoverage")
    private final CoverageStats branchCoverage;
    
    @JsonProperty("stuckPointScore")
    private final int stuckPointScore;
    
    @JsonProperty("analysisMetadata")
    private final AnalysisMetadata analysisMetadata;
    
    public StuckPointResult(CoverageLineInfo lineInfo, int score) {
        this.classFqn = lineInfo.getClassFqn();
        this.fileName = lineInfo.getFileName();
        this.lineNumber = lineInfo.getLineNumber();
        this.coverageStatus = lineInfo.getCoverageStatus();
        this.instructionCoverage = new CoverageStats(
            lineInfo.getInstructionsTotal(),
            lineInfo.getInstructionsCovered(),
            lineInfo.getInstructionCoverageRatio()
        );
        this.branchCoverage = new CoverageStats(
            lineInfo.getBranchesTotal(),
            lineInfo.getBranchesCovered(),
            lineInfo.getBranchCoverageRatio()
        );
        this.stuckPointScore = score;
        this.analysisMetadata = new AnalysisMetadata();
    }
    
    // Getters
    public String getClassFqn() { return classFqn; }
    public String getFileName() { return fileName; }
    public int getLineNumber() { return lineNumber; }
    public String getCoverageStatus() { return coverageStatus; }
    public CoverageStats getInstructionCoverage() { return instructionCoverage; }
    public CoverageStats getBranchCoverage() { return branchCoverage; }
    public int getStuckPointScore() { return stuckPointScore; }
    public AnalysisMetadata getAnalysisMetadata() { return analysisMetadata; }
    
    /**
     * Coverage statistics for instructions or branches
     */
    public static class CoverageStats {
        @JsonProperty("total")
        private final int total;
        
        @JsonProperty("covered")
        private final int covered;
        
        @JsonProperty("missed")
        private final int missed;
        
        @JsonProperty("ratio")
        private final double ratio;
        
        public CoverageStats(int total, int covered, double ratio) {
            this.total = total;
            this.covered = covered;
            this.missed = total - covered;
            this.ratio = ratio;
        }
        
        public int getTotal() { return total; }
        public int getCovered() { return covered; }
        public int getMissed() { return missed; }
        public double getRatio() { return ratio; }
    }
    
    /**
     * Metadata about the analysis process
     */
    public static class AnalysisMetadata {
        @JsonProperty("analysisType")
        private final String analysisType = "sootup-icfg";
        
        @JsonProperty("scoreCalculated")
        private final boolean scoreCalculated = true;
        
        @JsonProperty("notes")
        private final String notes = "Score calculation using SootUp ICFG analysis";
        
        public String getAnalysisType() { return analysisType; }
        public boolean isScoreCalculated() { return scoreCalculated; }
        public String getNotes() { return notes; }
    }
    
    @Override
    public String toString() {
        return String.format("%s:%d (score: %d, status: %s)", 
                           classFqn, lineNumber, stuckPointScore, coverageStatus);
    }
}