package executor;

/*
Here's the example of the target class:

import java.util.*;
import java.io.*;
import java.nio.*;
import java.nio.file.Files;
import java.nio.file.Path;

class Test {
    public static int[] getExpectedValues() {
        int[] ret = {0, 1, 2, 3};
        return ret;
    }

    public static int targetFunction(byte[] data) {
        try {
            return startSymbolicExecutionBytes(data);
        } catch (Throwable t) {
            return -1;
        }
    }

    public static int startSymbolicExecutionBytes(byte[] data) throws Throwable, Exception {
        String s0 = new String(data);
        if (s0.charAt(3) == 'A') {
            return 1;
        }
        if (s0.getBytes()[4] == 'B') {
            if (s0.getBytes()[4] == 'C') {
                // Unreachable case
                return 4;
            }
            return 2;
        }

        if (s0.charAt(4) + s0.getBytes()[5] == 'Z') {
            return 3;
        }
        return 0;
    }

    public static void main(String[] args) throws Throwable, Exception {
        Path path = Path.of(args[0]);
        byte[] data = Files.readAllBytes(path);
        int ret = startSymbolicExecutionBytes(data);
        System.out.println("RET " + ret);
    }
}
*/

import com.oracle.truffle.api.concolic.*;

import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Instrument;
import org.graalvm.polyglot.Value;
import org.graalvm.polyglot.HostAccess;
import org.graalvm.polyglot.EnvironmentAccess;
import org.graalvm.polyglot.PolyglotAccess;
import org.graalvm.polyglot.PolyglotException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.ByteBuffer;
import java.util.List;
import java.util.HashMap;
import java.util.Base64;
import java.util.concurrent.*;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.time.Duration;

import java.net.Socket;
import java.io.*;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.DefaultParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class Validator {
    public static final String languageId = "java";

    public static CommandLine parseArgs(String[] args) {
        Options options = new Options();

        options.addOption(Option.builder("c")
                .longOpt("concolic-classpath")
                .hasArg(true)
                .required(true)
                .desc("Classpath for running the target")
                .build());
        options.addOption(Option.builder("T")
                .longOpt("concolic-target")
                .hasArg(true)
                .required(true)
                .desc("Validator manager classname")
                .build());
        // Int-type size option for blob input. default is 1024
        options.addOption(Option.builder("s")
                .longOpt("size")
                .hasArg(true)
                .required(false)
                .desc("Size of the blob input")
                .build());
        CommandLineParser parser = new DefaultParser();
        CommandLine cmd = null;
        try {
            cmd = parser.parse(options, args);
        } catch(ParseException pe) {
            System.out.println("Error parsing cli arguments: " + pe.getMessage());
            HelpFormatter formatter = new HelpFormatter();
            formatter.printHelp("Validator", options);
            System.exit(1);
        }
        return cmd;
    }

    public static void main(String[] args) {
        CommandLine cmd = parseArgs(args);
        String classpath = cmd.getOptionValue("c");
        String target = cmd.getOptionValue("T");
        int blobSize = 1024;
        if (cmd.hasOption("s")) {
            blobSize = Integer.parseInt(cmd.getOptionValue("s"));
        }
        System.out.println("Classpath: " + classpath);
        System.out.println("Validator supporter classname: " + target);
        System.out.println("Blob size: " + blobSize);
        Context.Builder contextBuilder = Context.newBuilder(languageId);
        contextBuilder = contextBuilder.allowAllAccess(true);
        contextBuilder = contextBuilder.option("java.Classpath", classpath);
        Context context = contextBuilder.build();
        context.initialize(languageId);

        Value tracingTargetClass = context.getBindings(languageId).getMember(target);
        // Get the expected return value array of the main method
        Value expectedValues = tracingTargetClass.invokeMember("getExpectedValues/()[I");
        List<Integer> expectedValuesList = new ArrayList<>();
        for (int i = 0; i < expectedValues.getArraySize(); i++) {
            expectedValuesList.add(expectedValues.getArrayElement(i).asInt());
        }
        System.out.println("Expected return value array: " + expectedValuesList);

        // Build the input blob 
        HashSet<byte[]> todoBlobs = new HashSet<>();
        byte[] initBlob = new byte[blobSize];
        for (int i = 0; i < blobSize; i++) {
            initBlob[i] = (byte) 0;
        }
        todoBlobs.add(initBlob);

        // Run the target function repeatedly
        Set<Integer> visitedReturnValues = new HashSet<>();
        HashSet<Integer> visitedAllBranchCasesHash = new HashSet<>();
        while (true) {
            if (todoBlobs.isEmpty()) {
                break;
            }
            byte[] inputBlob = todoBlobs.iterator().next();
            todoBlobs.remove(inputBlob);

            // Clear the state
            ConstraintManager.clearBlobs();
            ConcolicBranch.clearBranchList();
            ConcolicHelper.reset();
            ConcolicVariableInfo.reset();
            ConcolicValueHelper.resetVariableCount();
            ConcolicObject.reset();

            // Set the original blob
            ConstraintManager.setOriginalBlob(inputBlob);

            // Build the input blob 
            Value byteArrayType = context.getBindings(languageId).getMember("[B");
            Value argsArray = byteArrayType.newInstance(blobSize);
            for (int i = 0; i < inputBlob.length; i++) {
                argsArray.setArrayElement(i, inputBlob[i]);
            }
            Value result = tracingTargetClass.invokeMember("targetFunction/([B)I", argsArray);
            System.out.println("Target result: " + result.asInt());
            visitedReturnValues.add(result.asInt());
            if (visitedReturnValues.size() == expectedValuesList.size()) {
                break;
            }

            // Try to process constraints
            ConstraintManager.processConstraints();

            // Check if the tried branch cases are all visited
            List<ConstraintManager.BranchCase> visitedBranchCases = ConstraintManager.getVisitedBranchCases();
            int visitedBranchCasesHash = visitedBranchCases.hashCode();
            if (visitedAllBranchCasesHash.contains(visitedBranchCasesHash)) {
                continue;
            }
            visitedAllBranchCasesHash.add(visitedBranchCasesHash);

            // Dump the visited branch cases
            System.out.println("Faced new branch cases:");
            for (ConstraintManager.BranchCase branchCase : visitedBranchCases) {
                System.out.println("  " + branchCase.toString());
            }

            // Get the solutions
            List<byte[]> newBlobs = ConstraintManager.getGeneratedBlobs();
            for (int i = 0; i < newBlobs.size(); i++) {
                todoBlobs.add(newBlobs.get(i));
            }
        }

        // TODO: It cannot search all branches deeply. Need to be analyzed.

        System.out.println("All branches visited");
        System.out.println("Expected return values: " + expectedValuesList);
        System.out.println("Visited return values: " + visitedReturnValues);
        if (visitedReturnValues.equals(new HashSet<>(expectedValuesList))) {
            System.out.println("All expected return values visited");
        } else {
            System.out.println("Not all expected return values visited:");
            HashSet<Integer> notVisited = new HashSet<>(expectedValuesList);
            notVisited.removeAll(visitedReturnValues);
            for (Integer expectedValue : notVisited) {
                System.out.println("  " + expectedValue);
            }
        }
        return;
    }
}