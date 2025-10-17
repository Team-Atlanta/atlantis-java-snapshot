package demo;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Queue;
import java.util.Set;

import org.apache.commons.cli.*;

import sootup.analysis.interprocedural.icfg.JimpleBasedInterproceduralCFG;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.jimple.basic.StmtPositionInfo;
import sootup.core.model.Position;
import sootup.core.jimple.common.stmt.Stmt;
import sootup.core.model.Body;
import sootup.core.model.SootMethod;
import sootup.core.signatures.MethodSignature;
import sootup.core.types.ClassType;
import sootup.java.bytecode.frontend.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.views.JavaView;

public class ICFGDemo {

    public static void main(String[] args) {
        // Parse command line arguments
        Options options = createOptions();
        CommandLineParser parser = new DefaultParser();
        
        try {
            CommandLine cmd = parser.parse(options, args);
            
            if (cmd.hasOption("help")) {
                printHelp(options);
                return;
            }
            
            String classpath = cmd.getOptionValue("classpath", "src/test/resources/sample");
            String entryClass = cmd.getOptionValue("class", "SampleClass");
            String entryMethod = cmd.getOptionValue("method", "main");
            String returnType = cmd.getOptionValue("return", "void");
            String[] paramTypes = cmd.getOptionValues("params");
            if (paramTypes == null) {
                paramTypes = new String[]{"java.lang.String[]"};
            }
            
            System.out.println("Starting ICFG Demo...");
            System.out.println("Classpath: " + classpath);
            System.out.println("Entry class: " + entryClass);
            System.out.println("Entry method: " + entryMethod);
            
            runAnalysis(classpath, entryClass, entryMethod, returnType, paramTypes);
            
        } catch (ParseException e) {
            System.err.println("Error parsing arguments: " + e.getMessage());
            printHelp(options);
        }
    }
    
    private static Options createOptions() {
        Options options = new Options();
        
        options.addOption(Option.builder("cp")
                .longOpt("classpath")
                .hasArg()
                .desc("Classpath for analysis (directory or JAR file)")
                .build());
                
        options.addOption(Option.builder("c")
                .longOpt("class")
                .hasArg()
                .desc("Entry class name (fully qualified)")
                .build());
                
        options.addOption(Option.builder("m")
                .longOpt("method")
                .hasArg()
                .desc("Entry method name")
                .build());
                
        options.addOption(Option.builder("r")
                .longOpt("return")
                .hasArg()
                .desc("Return type of entry method")
                .build());
                
        options.addOption(Option.builder("p")
                .longOpt("params")
                .hasArgs()
                .desc("Parameter types of entry method")
                .build());
                
        options.addOption(Option.builder("h")
                .longOpt("help")
                .desc("Show help message")
                .build());
                
        return options;
    }
    
    private static void printHelp(Options options) {
        HelpFormatter formatter = new HelpFormatter();
        formatter.printHelp("ICFGDemo", options);
        System.out.println("\nExamples:");
        System.out.println("  java -cp target/classes demo.ICFGDemo");
        System.out.println("  java -cp target/classes demo.ICFGDemo --classpath /path/to/project.jar --class com.example.Main");
        System.out.println("  java -cp target/classes demo.ICFGDemo --classpath /path/to/classes --class MyClass --method process --return int --params java.lang.String");
    }
    
    private static void runAnalysis(String classpath, String entryClass, String entryMethod, 
                                   String returnType, String[] paramTypes) {
        // Create input location pointing to the specified classpath
        List<AnalysisInputLocation> inputLocations = new ArrayList<>();
        
        // Support multiple classpath entries separated by colon
        String[] classpathEntries = classpath.split(":");
        for (String entry : classpathEntries) {
            inputLocations.add(new JavaClassPathAnalysisInputLocation(entry));
        }
        
        // Create JavaView to access classes
        JavaView view = new JavaView(inputLocations);
        
        // Get the entry class
        ClassType classType = view.getIdentifierFactory().getClassType(entryClass);
        
        // Define entry point method
        MethodSignature entryMethodSignature = view.getIdentifierFactory()
                .getMethodSignature(
                    classType, 
                    entryMethod, 
                    returnType, 
                    Arrays.asList(paramTypes)
                );
        
        System.out.println("Entry method signature: " + entryMethodSignature);
        
        // Initialize JimpleBasedInterproceduralCFG
        JimpleBasedInterproceduralCFG icfg = new JimpleBasedInterproceduralCFG(
            view,
            Collections.singletonList(entryMethodSignature),
            false,  // enableExceptions
            false   // includeReflectiveCalls
        );
        
        System.out.println("ICFG initialized successfully!");
        
        // Traverse ICFG starting from entry method and collect first 100 statements
        List<StatementInfo> statements = new ArrayList<>();
        
        // Get the entry method
        var entryMethodOpt = view.getMethod(entryMethodSignature);
        if (!entryMethodOpt.isPresent()) {
            System.err.println("Entry method not found: " + entryMethodSignature);
            return;
        }
        
        SootMethod entrySootMethod = entryMethodOpt.get();
        if (!entrySootMethod.hasBody()) {
            System.err.println("Entry method has no body: " + entryMethodSignature);
            return;
        }
        
        // BFS traversal of ICFG
        Queue<Stmt> worklist = new LinkedList<>();
        Set<Stmt> visited = new HashSet<>();
        
        // Start from entry points of the entry method
        Collection<Stmt> startPoints = icfg.getStartPointsOf(entrySootMethod);
        for (Stmt startPoint : startPoints) {
            worklist.add(startPoint);
            visited.add(startPoint);
        }
        
        // Traverse ICFG using BFS
        while (!worklist.isEmpty() && statements.size() < 100) {
            Stmt currentStmt = worklist.poll();
            
            // Create statement info for current statement
            SootMethod method = icfg.getMethodOf(currentStmt);
            if (method != null && method.hasBody()) {
                Body body = method.getBody();
                StatementInfo stmtInfo = new StatementInfo(
                    currentStmt,
                    method.getSignature(),
                    getLineNumbers(currentStmt, body),
                    getClassName(method.getSignature()),
                    getFileName(method.getSignature())
                );
                statements.add(stmtInfo);
            }
            
            // Add successors within the same method
            List<Stmt> successors = icfg.getSuccsOf(currentStmt);
            for (Stmt successor : successors) {
                if (!visited.contains(successor)) {
                    visited.add(successor);
                    worklist.add(successor);
                }
            }
            
            // Handle interprocedural calls - add entry points of called methods
            if (icfg.isCallStmt(currentStmt)) {
                Collection<SootMethod> callees = icfg.getCalleesOfCallAt(currentStmt);
                for (SootMethod callee : callees) {
                    if (callee.hasBody()) {
                        Collection<Stmt> calleeStartPoints = icfg.getStartPointsOf(callee);
                        for (Stmt startPoint : calleeStartPoints) {
                            if (!visited.contains(startPoint)) {
                                visited.add(startPoint);
                                worklist.add(startPoint);
                            }
                        }
                    }
                }
            }
        }
        
        // Print first 100 statements with position information
        System.out.println("\n=== First 100 Statements with Position Information ===");
        int count = 0;
        for (StatementInfo stmtInfo : statements) {
            if (count >= 100) break;
            
            System.out.printf("[%3d] Class: %s\n", count + 1, stmtInfo.className);
            System.out.printf("      File: %s\n", stmtInfo.fileName);
            System.out.printf("      Method: %s\n", stmtInfo.methodSignature);
            
            // Print line numbers as array
            if (stmtInfo.lineNumbers.length == 1) {
                System.out.printf("      Line: %d\n", stmtInfo.lineNumbers[0]);
            } else {
                System.out.printf("      Lines: %s\n", java.util.Arrays.toString(stmtInfo.lineNumbers));
            }
            
            System.out.printf("      Stmt: %s\n", stmtInfo.statement);
            System.out.printf("      Type: %s\n", stmtInfo.statement.getClass().getSimpleName());
            
            // Try to get actual source line number from position info
            StmtPositionInfo posInfo = stmtInfo.statement.getPositionInfo();
            Position pos = posInfo.getStmtPosition();
            if (pos.getFirstLine() > 0) {
                System.out.printf("      Source Line: %s, last col: %d\n", pos.toString(), pos.getLastCol());
            }
            
            // Check if this is a call statement and show targets
            if (icfg.isCallStmt(stmtInfo.statement)) {
                var callees = icfg.getCalleesOfCallAt(stmtInfo.statement);
                if (!callees.isEmpty()) {
                    System.out.printf("      Callees: %s\n", callees);
                }
            }
            
            System.out.println();
            count++;
        }
        
        System.out.println("Total statements found: " + statements.size());
        System.out.println("Demo completed successfully!");
    }
    
    private static int[] getLineNumbers(Stmt stmt, Body body) {
        // Try to get line numbers from position info if available
        StmtPositionInfo posInfo = stmt.getPositionInfo();
        Position pos = posInfo.getStmtPosition();
        
        if (pos.getFirstLine() > 0) {
            // Collect all lines from first to last, then filter out lines with invalid column info
            List<Integer> allLines = new ArrayList<>();
            
            // Add all lines from first to last
            for (int line = pos.getFirstLine(); line <= pos.getLastLine(); line++) {
                allLines.add(line);
            }
            
            // Filter out lines with invalid column info
            List<Integer> validLines = new ArrayList<>();
            for (int line : allLines) {
                if ((line == pos.getFirstLine() && pos.getFirstCol() < 0) ||
                    (line == pos.getLastLine() && pos.getLastCol() < 0)) {
                    continue; // Skip lines with invalid column info
                }
                validLines.add(line);
            }
            
            if (!validLines.isEmpty()) {
                return validLines.stream().mapToInt(Integer::intValue).toArray();
            }
        }
        
        // Fallback: use the index in the statement list as a simple position indicator
        List<Stmt> stmts = body.getStmts();
        return new int[]{stmts.indexOf(stmt) + 1};
    }
    
    private static String getClassName(MethodSignature methodSig) {
        return methodSig.getDeclClassType().getFullyQualifiedName();
    }
    
    private static String getFileName(MethodSignature methodSig) {
        String className = methodSig.getDeclClassType().getClassName();
        return className + ".java";
    }
    
    // Helper class to store statement information
    static class StatementInfo {
        final Stmt statement;
        final MethodSignature methodSignature;
        final int[] lineNumbers;
        final String className;
        final String fileName;
        
        StatementInfo(Stmt statement, MethodSignature methodSignature, int[] lineNumbers, 
                     String className, String fileName) {
            this.statement = statement;
            this.methodSignature = methodSignature;
            this.lineNumbers = lineNumbers;
            this.className = className;
            this.fileName = fileName;
        }
    }
}