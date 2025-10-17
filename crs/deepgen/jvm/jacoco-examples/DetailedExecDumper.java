/*******************************************************************************
 * Copyright (c) 2009, 2025 Mountainminds GmbH & Co. KG and Contributors
 * This program and the accompanying materials are made available under
 * the terms of the Eclipse Public License 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0
 *
 * SPDX-License-Identifier: EPL-2.0
 *
 * Contributors:
 *    Custom implementation for detailed coverage dumping
 *
 *******************************************************************************/
package org.jacoco.examples;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.util.Date;

import org.jacoco.core.analysis.Analyzer;
import org.jacoco.core.analysis.CoverageBuilder;
import org.jacoco.core.analysis.IClassCoverage;
import org.jacoco.core.analysis.ICounter;
import org.jacoco.core.data.ExecutionDataStore;
import org.jacoco.core.data.ExecutionDataReader;
import org.jacoco.core.data.SessionInfoStore;

/**
 * This example reads execution data files and class files to provide detailed
 * line-by-line coverage information including FQN, file name, and coverage status.
 */
public final class DetailedExecDumper {

    private final PrintStream out;

    /**
     * Creates a new dumper instance printing to the given stream.
     *
     * @param out stream for outputs
     */
    public DetailedExecDumper(final PrintStream out) {
        this.out = out;
    }

    /**
     * Run this dumper with the given parameters.
     *
     * @param execFile execution data file (.exec)
     * @param classFiles class files or directories containing class files
     * @throws IOException in case of error reading files
     */
    public void execute(final String execFile, final String[] classFiles) throws IOException {
        out.printf("=== JaCoCo Detailed Coverage Report ===%n");
        out.printf("Execution file: %s%n", execFile);
        out.printf("Generated: %s%n%n", new Date());

        // Load execution data
        final ExecutionDataStore executionData = new ExecutionDataStore();
        final SessionInfoStore sessionInfos = new SessionInfoStore();
        
        final FileInputStream in = new FileInputStream(execFile);
        final ExecutionDataReader reader = new ExecutionDataReader(in);
        reader.setSessionInfoVisitor(sessionInfos);
        reader.setExecutionDataVisitor(executionData);
        reader.read();
        in.close();

        // Analyze coverage
        final CoverageBuilder coverageBuilder = new CoverageBuilder();
        final Analyzer analyzer = new Analyzer(executionData, coverageBuilder);

        // Analyze all class files
        for (final String classFile : classFiles) {
            analyzer.analyzeAll(new File(classFile));
        }

        // Output detailed coverage information
        out.println("FORMAT: FQN | FileName | LineNumber | CoverageStatus");
        out.println("=".repeat(80));

        for (final IClassCoverage classCoverage : coverageBuilder.getClasses()) {
            dumpClassCoverage(classCoverage);
        }

        // Summary
        out.printf("%n=== Summary ===%n");
        out.printf("Total classes analyzed: %d%n", coverageBuilder.getClasses().size());
    }

    private void dumpClassCoverage(final IClassCoverage classCoverage) {
        final String fqn = classCoverage.getName().replace('/', '.');
        final String fileName = getFileName(classCoverage.getName());
        
        // Print class header
        out.printf("%n--- Class: %s ---%n", fqn);
        out.printf("Source file: %s%n", fileName);
        out.printf("Instructions: %d/%d covered%n", 
                classCoverage.getInstructionCounter().getCoveredCount(),
                classCoverage.getInstructionCounter().getTotalCount());
        out.printf("Branches: %d/%d covered%n", 
                classCoverage.getBranchCounter().getCoveredCount(),
                classCoverage.getBranchCounter().getTotalCount());
        out.printf("Lines: %d/%d covered%n", 
                classCoverage.getLineCounter().getCoveredCount(),
                classCoverage.getLineCounter().getTotalCount());
        out.println();

        // Print line-by-line coverage
        final int firstLine = classCoverage.getFirstLine();
        final int lastLine = classCoverage.getLastLine();
        
        if (firstLine > 0) {
            for (int lineNumber = firstLine; lineNumber <= lastLine; lineNumber++) {
                final int status = classCoverage.getLine(lineNumber).getStatus();
                // Only show lines that have coverage information (skip empty lines)
                if (classCoverage.getLine(lineNumber).getInstructionCounter().getTotalCount() > 0) {
                    out.printf("%s | %s | %d | %s%n", 
                            fqn, 
                            fileName, 
                            lineNumber, 
                            getCoverageStatusString(status));
                }
            }
        } else {
            out.printf("%s | %s | N/A | NO_SOURCE_INFO%n", fqn, fileName);
        }
    }

    private String getFileName(final String className) {
        // Extract simple class name from fully qualified path
        final int lastSlash = className.lastIndexOf('/');
        if (lastSlash >= 0) {
            final String simpleName = className.substring(lastSlash + 1);
            return simpleName + ".java";
        }
        return className + ".java";
    }

    private String getCoverageStatusString(final int status) {
        switch (status) {
            case ICounter.NOT_COVERED:
                return "NOT_COVERED";
            case ICounter.PARTLY_COVERED:
                return "PARTLY_COVERED";
            case ICounter.FULLY_COVERED:
                return "FULLY_COVERED";
            default:
                return "UNKNOWN";
        }
    }

    /**
     * Entry point to run this dumper as a Java application.
     *
     * Usage: java DetailedExecDumper <exec_file> <class_file_or_directory> [<class_file_or_directory> ...]
     *
     * @param args list of program arguments
     * @throws IOException in case of errors executing the dumper
     */
    public static void main(final String[] args) throws IOException {
        if (args.length < 2) {
            System.err.println("Usage: java DetailedExecDumper <exec_file> <class_file_or_directory> [<class_file_or_directory> ...]");
            System.err.println();
            System.err.println("Examples:");
            System.err.println("  java DetailedExecDumper coverage.exec target/classes");
            System.err.println("  java DetailedExecDumper jacoco.exec build/classes/java/main");
            System.exit(1);
        }

        final String execFile = args[0];
        final String[] classFiles = new String[args.length - 1];
        System.arraycopy(args, 1, classFiles, 0, args.length - 1);

        new DetailedExecDumper(System.out).execute(execFile, classFiles);
    }
}