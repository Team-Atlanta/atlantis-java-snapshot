package stuck.point.analyzer;

import org.apache.commons.cli.*;
import java.io.IOException;
import java.util.List;

/**
 * Main entry point for the Stuck Point Analyzer tool.
 * 
 * This tool combines JaCoCo coverage analysis with SootUp static analysis to identify
 * and score fuzzing stuck points. It analyzes partly covered lines from JaCoCo execution
 * data and uses SootUp's ICFG to calculate reachability scores.
 */
public class StuckPointAnalyzer {

    public static void main(String[] args) {
        Options options = createOptions();
        CommandLineParser parser = new DefaultParser();
        
        try {
            CommandLine cmd = parser.parse(options, args);
            
            if (cmd.hasOption("help")) {
                printUsage(options);
                return;
            }
            
            // Validate required arguments
            if (!cmd.hasOption("exec") || !cmd.hasOption("jars") || !cmd.hasOption("entry") || 
                !cmd.hasOption("metadata") || !cmd.hasOption("source-dir") || !cmd.hasOption("annotated-output-dir")) {
                System.err.println("Error: Missing required arguments");
                printUsage(options);
                System.exit(1);
            }
            
            String execFile = cmd.getOptionValue("exec");
            String[] jarFiles = cmd.getOptionValues("jars");
            String entryPoint = cmd.getOptionValue("entry");
            String outputFile = cmd.getOptionValue("output", "stuck-points.json");
            boolean verbose = cmd.hasOption("verbose");
            String metadataFile = cmd.getOptionValue("metadata");
            String sourceDir = cmd.getOptionValue("source-dir");
            String annotatedOutputDir = cmd.getOptionValue("annotated-output-dir");
            
            // Initialize and run the analyzer
            StuckPointAnalyzerCore analyzer = new StuckPointAnalyzerCore(verbose);
            analyzer.analyze(execFile, jarFiles, entryPoint, outputFile, metadataFile, sourceDir, annotatedOutputDir);
            
        } catch (ParseException e) {
            System.err.println("Error parsing command line: " + e.getMessage());
            printUsage(options);
            System.exit(1);
        } catch (Exception e) {
            System.err.println("Analysis failed: " + e.getMessage());
            // Always print full stack trace for debugging
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    private static Options createOptions() {
        Options options = new Options();
        
        options.addOption(Option.builder("e")
                .longOpt("exec")
                .hasArg()
                .required()
                .desc("Path to JaCoCo execution data file (.exec)")
                .build());
                
        options.addOption(Option.builder("j")
                .longOpt("jars")
                .hasArgs()
                .required()
                .desc("Paths to JAR files or class directories to analyze")
                .build());
                
        options.addOption(Option.builder("entry")
                .longOpt("entrypoint")
                .hasArg()
                .required()
                .desc("Entry point method signature (e.g., 'com.example.Main.main(java.lang.String[])')")
                .build());
                
        options.addOption(Option.builder("o")
                .longOpt("output")
                .hasArg()
                .desc("Output JSON file path (default: stuck-points.json)")
                .build());
                
        options.addOption(Option.builder("v")
                .longOpt("verbose")
                .desc("Enable verbose output")
                .build());
                
        options.addOption(Option.builder("m")
                .longOpt("metadata")
                .hasArg()
                .required()
                .desc("Path to CP metadata JSON file (required)")
                .build());
                
        options.addOption(Option.builder("s")
                .longOpt("source-dir")
                .hasArg()
                .required()
                .desc("Original source directory root path to copy from (required)")
                .build());
                
        options.addOption(Option.builder("a")
                .longOpt("annotated-output-dir")
                .hasArg()
                .required()
                .desc("Directory where annotated source code will be written (required)")
                .build());
                
        options.addOption(Option.builder("h")
                .longOpt("help")
                .desc("Show help message")
                .build());
                
        return options;
    }
    
    private static void printUsage(Options options) {
        HelpFormatter formatter = new HelpFormatter();
        formatter.printHelp("stuck-point-analyzer", 
            "Analyze fuzzing stuck points using JaCoCo coverage and SootUp static analysis\n\n",
            options,
            "\nExamples:\n" +
            "  stuck-point-analyzer -e coverage.exec -j target/classes --entry com.example.Main.main -m metadata.json -s /src --annotated-output-dir /tmp/annotated\n" +
            "  stuck-point-analyzer --exec jacoco.exec --jars app.jar --entrypoint com.test.Fuzzer.fuzz --metadata meta.json --source-dir /project/src --annotated-output-dir /tmp/out --output results.json\n\n" +
            "The tool identifies lines with partial coverage from JaCoCo data and uses SootUp ICFG analysis\n" +
            "to calculate reachability scores for each stuck point.",
            true);
    }
}