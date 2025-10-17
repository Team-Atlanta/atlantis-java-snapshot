package executor;

import com.oracle.truffle.api.concolic.*;

import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Instrument;
import org.graalvm.polyglot.Value;
import org.graalvm.polyglot.HostAccess;
import org.graalvm.polyglot.EnvironmentAccess;
import org.graalvm.polyglot.PolyglotAccess;
import org.graalvm.polyglot.PolyglotException;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.ByteBuffer;
import java.time.Duration;

import java.net.Socket;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Collectors;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.DefaultParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;

import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

public class App {
    public static int pid = 0;
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
                .desc("Target classname")
                .build());
        options.addOption(Option.builder("A")
                .longOpt("concolic-args")
                .hasArg(true)
                .required(false)
                .desc("Target arguments")
                .build());
        options.addOption(Option.builder("D")
                .longOpt("harness-id")
                .hasArg(true)
                .required(false)
                .desc("Harness ID")
                .build());
        options.addOption(Option.builder("J")
                .longOpt("java-home")
                .hasArg(true)
                .required(false)
                .desc("Java home")
                .build());
        options.addOption(Option.builder("O")
                .longOpt("outdir")
                .hasArg(true)
                .required(true)
                .desc("Output directory")
                .build());
        options.addOption(Option.builder("P")
                .longOpt("pid")
                .hasArg(true)
                .required(false)
                .desc("Execution ID")
                .build());
        options.addOption(Option.builder("Z")
                .longOpt("timeout")
                .hasArg(true)
                .required(false)
                .desc("Timeout value in sec")
                .build());
        options.addOption(Option.builder("S")
                .longOpt("server")
                .hasArg(true)
                .required(true)
                .desc("port_number (non-zero) if server 0 if not-server")
                .build());
        options.addOption(Option.builder("L")
                .longOpt("logging")
                .hasArg(false)
                .required(false)
                .desc("enable JIT logging behavior (Logging only if JIT is finished)")
                .build());
        options.addOption(Option.builder("N")
                .longOpt("ncores")
                .hasArg(true)
                .required(false)
                .desc("number of cores assigned to the executor")
                .build());
        options.addOption(Option.builder("R")
                .longOpt("scheduler-port")
                .hasArg(true)
                .required(false)
                .desc("Scheduler port")
                .build());


        CommandLineParser parser = new DefaultParser();
        CommandLine cmd = null;
        try {
            cmd = parser.parse(options, args);
        } catch(ParseException pe) {
            System.out.println("Error parsing cli arguments: " + pe.getMessage());
            HelpFormatter formatter = new HelpFormatter();
            formatter.printHelp("Executor", options);
            System.exit(1);
        }
        return cmd;
    }

    // blobs to dir, filename as system time
    public static void saveBlobsToDir(List<byte[]> blobs, List<String> branchIdentifiers, String dstDir, int rid) throws IOException {
        Path dirPath = Paths.get(dstDir);
        if (!Files.exists(dirPath)) {
            Files.createDirectories(dirPath);
        }

        long time = System.currentTimeMillis();
        int cnt = 0;
        //for (byte[] blob : blobs) {
        for (int i=0; i<blobs.size(); i++) {
            byte[] blob = blobs.get(i);
            String branchIdentifier = branchIdentifiers.get(i);
            if (branchIdentifier.length() > 127) {
                branchIdentifier = branchIdentifier.substring(0, 127);
            }
            cnt++;
            String fileName = "blob-" + time + String.format("-%06d-", cnt) + branchIdentifier + "-pid-" + pid + "-rid-" + rid + ".bin";
            Path outputPath = dirPath.resolve(fileName);
            Files.write(outputPath, blob);
            System.out.println("[Executor] Saved blob to: " + outputPath.toAbsolutePath());

        }
    }


    public static void resetStaticMembers() {
        ConstraintManager.clearBlobs();
        ConcolicBranch.clearBranchList();
        ConcolicHelper.reset();
        ConcolicVariableInfo.reset();
        ConcolicValueHelper.resetVariableCount();
        ConcolicObject.reset();
        Z3Helper.resetContext();
    }

    private static String getObjenesisVersion(String mockito_version) {
/*
- objenesis 1.0
    - From mockito-core 1.3 to 1.9.5-rc1
- objenesis 2.1
    - From mockito-core 2.0.0-beta to 2.0.63-beta
- objenesis 2.4
    - From mockito-core 2.0.64-beta to 2.6.2
- objenesis 2.5
    - From mockito-core 2.6.3 to 2.8.47
- objenesis 2.6
    - From mockito-core 2.6.0 to 3.4.6
- objenesis 3.1
    - From mockito-core 3.5.0 to 3.8.0
- objenesis 3.2
    - From mockito-core 3.9.0 to 4.8.1
- objenesis 3.3
    - From mockito-core 4.9.0 to latest (5.16.1)
*/
        class Range {
            int major;
            int minor;
            int patch;
            String version;
            Range(int major, int minor, int patch, String version) {
                this.major = major;
                this.minor = minor;
                this.patch = patch;
                this.version = version;
            }
        }

        Range[] ranges = {
            new Range(1, 3, 0, "1.0"),
            new Range(2, 0, 0, "2.1"),
            new Range(2, 0, 64, "2.4"),
            new Range(2, 6, 3, "2.5"),
            new Range(2, 6, 0, "2.6"),
            new Range(3, 5, 0, "3.1"),
            new Range(3, 9, 0, "3.2"),
            new Range(4, 9, 0, "3.3"),
        };

        String[] mockito_versions = mockito_version.split("\\.");
        int[] version_nums = new int[3];
        for (int i = 0; i < 3; i++) {
            if (mockito_versions.length <= i) {
                version_nums[i] = 0;
            } else {
                String version_num = mockito_versions[i];
                version_num = version_num.replaceAll("[^0-9]", "");
                version_nums[i] = Integer.parseInt(version_num);
            }
        }

        for (int i = ranges.length - 1; i >= 0; i--) {
            Range range = ranges[i];
            if (version_nums[0] < range.major) {
                continue;
            }
            if (version_nums[0] > range.major) {
                return range.version;
            }
            if (version_nums[1] < range.minor) {
                continue;
            }
            if (version_nums[1] > range.minor) {
                return range.version;
            }
            if (version_nums[2] < range.patch) {
                continue;
            }
            return range.version;
        }

        throw new RuntimeException("Failed to find objenesis version for mockito version: " + mockito_version);
    }

    static long start_time = 0;

    public static void main(String[] args) {
        String cwd = System.getProperty("user.dir");
        if (!cwd.endsWith("/")) {
            cwd += "/";
        }
        if (cwd.endsWith("/app/")) {
            cwd = cwd.substring(0, cwd.length() - 5);
        }

        start_time = System.currentTimeMillis();

        // Check if LD_DEBUG is set to 'unused'
        String ldDebug = System.getenv("LD_DEBUG");
        if (ldDebug == null || !ldDebug.equals("unused")) {
            System.out.println("[Executor] LD_DEBUG is not set to 'unused'");
            System.exit(1);
        }

        // Print current java version and path
        System.out.println("[Executor] Current java version: " + System.getProperty("java.version"));
        System.out.println("[Executor] Current path: " + cwd);

        // option parsing
        CommandLine cmd = parseArgs(args);

        String classpath = null;
        String classname = null;
        String mainArg = null;
        String outDir = null;
        String pidString = null;
        String harnessId = null;
        String javaHome = null;
        int portNumber = 0;
        int ncores = 1;
        int timeoutInSecond = 2400;
        boolean jitLogging = false;
        int schedulerPort = -1;

        if (cmd.hasOption("c")) {
            classpath = cmd.getOptionValue("c");
        }
        if (cmd.hasOption("T")) {
            classname = cmd.getOptionValue("T");
        }
        if (cmd.hasOption("A")) {
            mainArg = cmd.getOptionValue("A");
        }
        if (cmd.hasOption("D")) {
            harnessId = cmd.getOptionValue("D");
        }
        if (cmd.hasOption("J")) {
            javaHome = cmd.getOptionValue("J");
        }
        if (cmd.hasOption("O")) {
            outDir = cmd.getOptionValue("O");
            ConstraintManager.outDir = outDir;
        }
        if (cmd.hasOption("P")) {
            pidString = cmd.getOptionValue("P");
            pid = Integer.valueOf(pidString).intValue();
            ConstraintManager.pid = pid;
        }
        if (cmd.hasOption("S")) {
            String serverString = cmd.getOptionValue("S");
            portNumber = Integer.valueOf(serverString).intValue();
        }
        if (cmd.hasOption("Z")) {
            String timeoutString = cmd.getOptionValue("Z");
            timeoutInSecond = Integer.valueOf(timeoutString).intValue();
        }
        if (cmd.hasOption("L")) {
            jitLogging = true;
        }
        if (cmd.hasOption("N")) {
            String ncoresString = cmd.getOptionValue("N");
            ncores = Integer.valueOf(ncoresString).intValue();
        }
        if (cmd.hasOption("R")) {
            String schedulerPortString = cmd.getOptionValue("R");
            schedulerPort = Integer.valueOf(schedulerPortString).intValue();
        }

        System.out.println("[Executor] classpath: " + classpath);
        System.out.println("[Executor] classname: " + classname);
        System.out.println("[Executor] harnessId: " + harnessId);
        System.out.println("[Executor] javaHome: " + javaHome);
        System.out.println("[Executor] mainArg: " + mainArg);
        System.out.println("[Executor] outDir: " + outDir);
        System.out.println("[Executor] pid: " + pid);
        System.out.println("[Executor] server port: " + portNumber);
        System.out.println("[Executor] ncores: " + ncores);
        System.out.println("[Executor] scheduler port: " + schedulerPort);

        Context.Builder contextBuilder = Context.newBuilder(languageId);
        contextBuilder = contextBuilder.allowAllAccess(true);
        /*
        contextBuilder = contextBuilder.allowPolyglotAccess(PolyglotAccess.NONE)
                                        .option("engine.Compilation", "true")
                                        .option("engine.BackgroundCompilation", "true");
        */
        // Add jar for objenesis
        for (String single_path : classpath.split(":")) {
            if (single_path.contains("mockito-core-")) {
                String mockito_version = single_path.split("mockito-core-")[1].split(".jar")[0];
                try {
                    String objenesis_version = getObjenesisVersion(mockito_version);
                    System.out.println("[Executor] objenesis_version: " + objenesis_version);
                    String objenesis_path = cwd + "/app/lib/jars/objenesis/objenesis-" + objenesis_version + ".jar";
                    System.out.println("[Executor] objenesis path   : " + objenesis_path);
                    classpath += ":" + objenesis_path;
                } catch (Exception e) {
                    System.out.println("[Executor] Failed to get objenesis version for mockito version: " + mockito_version);
                    e.printStackTrace();
                }
                break;
            }
        }

        // Add classpath for guiding mockito
        classpath += ":" + cwd;
        classpath += ":" + cwd + "/app";

        System.out.println("[Executor] classpath: " + classpath);

        contextBuilder = contextBuilder.option("java.Classpath", classpath);
        contextBuilder = contextBuilder.option("java.MultiThreaded", "true");

        // Add java agents
        System.out.println("[Executor] Adding java agents");
        int agentIdx = 0;
        for (String agent : classpath.split(":")) {
            if (agent.strip().isEmpty()) {
                continue;
            }
            if (agent.contains("byte-buddy-agent")) {
                String javaAgentHeader = "java.JavaAgent." + agentIdx;
                String javaAgentValue = agent;
                System.out.println("[Executor] Adding java agent: " + javaAgentHeader + "=" + javaAgentValue);
                contextBuilder = contextBuilder.option(javaAgentHeader, javaAgentValue);
                agentIdx++;
            }
        }

        System.out.println("[Executor] Java agents added!");
        // context builder
        Context context = contextBuilder.build();
        System.out.println("[Executor] Context built: " + context.getClass().getName().toString());
        context.initialize(languageId);
        /* test interrupt */
        /*
        try {
            context.interrupt(Duration.ofSeconds(timeoutInSecond));
        } catch (TimeoutException e) {
            System.out.println("[Executor] Execution finished, timeout cancelled!");
            // ignore
        }
        */
        System.out.println("[Executor] Context initialized!");
        if (portNumber == 0) {
            boolean genBlob = true;
            /*
            if (jitLogging) {
                Logger.compileLog = false;
                genBlob = false;
            }
            */
            run_for_single_exec(context, classpath, classname, mainArg, outDir, pid, portNumber, timeoutInSecond, genBlob, ncores);
            /*
            if (jitLogging) {
                Logger.compileLog = true;
                run_for_single_exec(context, classpath, classname, mainArg, outDir, pid, portNumber, timeoutInSecond, true, ncores);
            }
            */
        } else {
            run_for_service(context, contextBuilder, classpath, classname, mainArg, outDir, pid, portNumber, timeoutInSecond, harnessId, javaHome, jitLogging, schedulerPort, ncores);
        }
        context.close();
        System.out.println("[Executor] Execution Finished!");
    }

    public static HashMap<String, String> parseBlob(String jsonData) {
        Gson gson = new Gson();
        TypeToken<HashMap<String, String>> token = new TypeToken<HashMap<String, String>>() {};
        return gson.fromJson(jsonData, token);
    }

    public static void run_for_service(Context context,
                                        Context.Builder contextBuilder,
                                        String classpath,
                                        String classname, String mainArg,
                                        String outDir, int pid, int portNumber,
                                        int timeoutInSecond, String harnessId,
                                        String javaHome, boolean jitLogging,
                                        int schedulerPort, int ncores) {

        // disable log at start if jitLogging is enabled
        /*
        boolean loggingTurnedOn = false;
        if (jitLogging) {
            Logger.compileLog = false;
        }
        */

        CoverageManager coverageManager = new CoverageManager(harnessId, javaHome, schedulerPort);
        if (coverageManager.isEnabled()) {
            ConstraintManager.setCoverageManager(coverageManager);
        }

        // loop!
        while (true) {
            // connect to the server to get the blob info, read it and store it as original blob
            // not from mainArg; it must be from the server data
            //HashMap<String, String> blobInfo = parseBlob(mainArg);
            Socket socket = null;
            int blobCount = 0;
            String blob_fn_prefix = null;
            try {
                blob_fn_prefix = "";
                blobCount = 0;
                socket = new Socket("127.0.0.1", portNumber);
                OutputStream out = socket.getOutputStream();
                InputStream in = socket.getInputStream();

                out.write("SEED".getBytes("UTF-8"));
                out.flush();

                byte[] length_header = new byte[4];
                in.readNBytes(length_header, 0, 4);
                ByteBuffer buffer = ByteBuffer.wrap(length_header);
                int json_length = buffer.getInt();

                if (json_length == 0) {
                    continue;
                }

                byte[] json_bytes = new byte[json_length];
                int len_read = in.readNBytes(json_bytes, 0, json_length);
                start_time = System.currentTimeMillis();

                String json = new String(json_bytes);
                HashMap<String, String> blobInfo = parseBlob(json);

                byte[] blob = null;
                String className = null;
                String methodName = null;
                String methodDesc = null;
                int bytecodeOffset = -1;
                int rid = -1;

                for (String key : blobInfo.keySet()) {
                    String value = blobInfo.get(key);
                    switch (key) {
                        case "blob":
                            blob = Base64.getDecoder().decode(value);
                            break;
                        case "blob_fn_prefix":
                            blob_fn_prefix = value;
                            break;
                        case "class_name":
                            className = value;
                            break;
                        case "method_name":
                            methodName = value;
                            break;
                        case "method_desc":
                            methodDesc = value;
                            break;
                        case "rid":
                            rid = Integer.valueOf(value).intValue();
                            break;
                        default:
                            throw new RuntimeException("Unknown key in the blobInfo: " + key);
                    }
                }

                // clear blobs, and set json blob data as original blob
                resetStaticMembers();
                ConstraintManager.rid = rid;

                System.out.println("[Executor] json loaded, className: " + className + ", methodName: " + methodName + ", methodDesc: " + methodDesc + ", rid: " + rid + ", blob_fn_prefix: " + blob_fn_prefix);
                ConstraintManager.setOriginalBlob(blob);

                if (className != null && className.length() > 0) {
                    ConstraintManager.setTarget(className, methodName + methodDesc, bytecodeOffset);
                } else {
                    ConstraintManager.unsetTarget();
                }

                System.out.println("[Executor] pre execution blob length " + ConstraintManager.getGeneratedBlobs().size());
                System.out.println("[Executor] pre execption branchList length " + ConcolicBranch.getBranchList().size());

                System.out.println("[Executor] start execution for blob: " + blob_fn_prefix + ".blob");
                long before_main_time = System.currentTimeMillis();

                context.resetLimits();
                Config.getInstance().resetTimeoutInterrupted();

                long[] check_timeout_time = new long[2];
                check_timeout_time[0] = 0;

                // timeout thread
                Thread t = new Thread() {
                    @Override
                    public void run() {
                        try {
                            // sleep for timeout, it could be interrupted
                            Thread.sleep(timeoutInSecond * 1000);
                            // set the timeout flag
                            Config.getInstance().setTimeoutInterrupted();
                            // record the time when timeout has triggered
                            check_timeout_time[0] = System.currentTimeMillis();
                            System.out.println("[Executor-TimeoutThread] Timeout reached! Interrupting execution...");
                        } catch (InterruptedException e) {
                            System.out.println("[Executor-TimeoutThread] Execution finished, timeout cancelled!");
                            // ignore - well interrupted
                        } catch (PolyglotException e) {
                            System.out.println("[Executor-TimeoutThread] Polyglot Exception: " + e);
                            System.out.println("[Executor-TimeoutThread] isExit: " + e.isExit());
                            e.printStackTrace();
                        } catch (Exception e) {
                            System.out.println("[Executor-TimeoutThread] Exception: " + e);
                            e.printStackTrace();
                        }

                    }
                };

                t.start();


                String blob_path = null;
                try {
                    blob_path = blob_fn_prefix + ".blob";

                    // set coverage blog first
                    if (coverageManager.isEnabled()) {
                        coverageManager.updateSeed(blob_path, Arrays.asList(classpath.split(":")));
                    }

                    invoke_fuzzer(context, languageId, classname, blob);

                    // stop timeout thread if finished
                    t.interrupt();

                } catch (org.graalvm.polyglot.PolyglotException e) {
                    String message = e.getMessage();
                    if (message.contains("STOP")) {
                        System.out.println("[Executor-concolic] Timeout with exception: " + e);
                    } else {
                        try {
                            Thread.sleep(1000);
                        } catch (Exception ignored) {}
                        System.out.println("[Executor-concolic] Exception: " + e);
                        StringWriter sw = new StringWriter();
                        e.printStackTrace(new PrintWriter(sw));
                        System.out.println("[Executor-concolic] unhandled exception: " + sw.toString());
                        break;
                    }
                } catch (Exception e) {
                    try {
                        Thread.sleep(1000);
                    } catch (Exception ignored) {}
                    System.out.println("[Executor-concolic] Exception: " + e);
                    StringWriter sw = new StringWriter();
                    e.printStackTrace(new PrintWriter(sw));
                    System.out.println("[Executor-concolic] handled exception: " + sw.toString());
                }

                if (check_timeout_time[0] != 0) {
                    long timeout_finished = System.currentTimeMillis();
                    long post_timeout_execution_duration = timeout_finished - check_timeout_time[0];
                    System.out.println("[Executor] post timeout execution duration: " + post_timeout_execution_duration + " ms");
                }

                long before_constraint_solving_time = System.currentTimeMillis();
                ConstraintManager.processConstraints();
                // run one more time to solve them all!
                if (ConstraintManager.isTargetSet) {
                    ConstraintManager.unsetTarget();
                    ConstraintManager.processConstraints();
                }


                long after_constraint_solving_time = System.currentTimeMillis();

                List<byte[]> blobs = ConstraintManager.getGeneratedBlobs();
                List<String> branchIdentifiers = ConstraintManager.getBranchIdentifiers();
                System.out.println("[Executor] Generated " + blobs.size() + " blobs");
                blobCount = blobs.size();
                /*
                if (!outDir.isEmpty()) {
                    try {
                        saveBlobsToDir(blobs, branchIdentifiers, outDir, rid);
                    } catch (IOException e) {
                        System.out.println("[Executor] Failed to save: " + e);
                    }
                }
                */
                System.out.println("[Executor] blob length " + blobs.size());
                System.out.println("[Executor] branchList length " + ConcolicBranch.getBranchList().size());

                System.out.println("[Executor] post execution blob length " + ConstraintManager.getGeneratedBlobs().size());
                System.out.println("[Executor] post execption branchList length " + ConcolicBranch.getBranchList().size());

                long after_blob_gen_time = System.currentTimeMillis();

                System.out.println("[Executor] Pre-execution Time: " + (before_main_time - start_time) + " ms");
                System.out.println("[Executor] ConcolicExecution Time: " + (before_constraint_solving_time - before_main_time) + " ms");
                System.out.println("[Executor] Constraint Solving Time: " + (after_constraint_solving_time - before_constraint_solving_time) + " ms");
                System.out.println("[Executor] Blob Genenration Time: " + (after_blob_gen_time - after_constraint_solving_time) + " ms");
                System.out.println("[Executor] Total Time: " + (after_blob_gen_time - start_time) + " ms");
                if (blobs.size() > 0) {
                    System.out.println("[Executor] Average Constraint Solving Time: " + ((after_constraint_solving_time - before_constraint_solving_time) / blobs.size()) + " ms");
                }
                if (check_timeout_time[0] == 0) {
                    /*
                    // no timeout, if jitlogging is on, enable logging
                    if (jitLogging && !loggingTurnedOn) {
                        Logger.compileLog = true;
                        loggingTurnedOn = true;
                    }
                    */
                }
                start_time = System.currentTimeMillis();
            } catch (Exception e) {
                try {
                    Thread.sleep(1000);
                } catch (Exception ignored) {}
                System.out.println("[Executor] Execution error: " + e.getMessage());
                StringWriter sw = new StringWriter();
                e.printStackTrace(new PrintWriter(sw));
                System.out.println("[Executor] handled exception: " + sw.toString());
            } finally {
                if (socket != null) {
                    if (!socket.isClosed()){
                        try {
                            byte[] blobCountJsonBytes = ("{ \"blob_count\": " + blobCount + ", \"blob_fn_prefix\": \"" + blob_fn_prefix + "\" }").getBytes("UTF-8");
                            int blobCountJsonLength = blobCountJsonBytes.length;
                            byte[] blobCountJsonLengthBytes = ByteBuffer.allocate(4).putInt(blobCountJsonLength).array();
                            socket.getOutputStream().write(blobCountJsonLengthBytes);
                            socket.getOutputStream().write(blobCountJsonBytes);
                            socket.close();
                        } catch (IOException e) {
                            System.out.println("[Executor] Failed to send blob count: " + e);
                            StringWriter sw = new StringWriter();
                            e.printStackTrace(new PrintWriter(sw));
                            System.out.println("[Executor] handled exception: " + sw.toString());
                        }
                    }
                }
            }
        }
    }

    public static void run_for_single_exec(Context context, String classpath,
                                            String classname, String mainArg,
                                            String outDir, int pid,
                                            int portNumber,
                                            int timeoutInSecond,
                                            boolean genBlob,
                                            int ncores) {
        resetStaticMembers();

        // read blob -- directly from the file
        byte[] data = null;
        try {
            Path path = Path.of(mainArg);
            data = Files.readAllBytes(path);
            // set it as original blob
            ConstraintManager.setOriginalBlob(data);
        } catch (IOException e) {
            System.err.println(e.getMessage());
            e.printStackTrace();
        }

        long before_main_time = System.currentTimeMillis();
        try {
            invoke_fuzzer(context, languageId, classname, data);
        } catch (Exception e) {
            System.out.println("[Executor] Exception: " + e);
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            System.out.println("[Executor] handled exception: " + sw.toString());
        }

        if (!genBlob) {
            return;
        }

        long before_constraint_solving_time = System.currentTimeMillis();
        ConstraintManager.processConstraints();

        // run one more time to solve them all!
        if (ConstraintManager.isTargetSet) {
            ConstraintManager.unsetTarget();
            ConstraintManager.processConstraints();
        }

        long after_constraint_solving_time = System.currentTimeMillis();

        List<byte[]> blobs = ConstraintManager.getGeneratedBlobs();
        List<String> branchIdentifiers = ConstraintManager.getBranchIdentifiers();
        System.out.println("[Executor] Generated " + blobs.size() + " blobs");
        /*
        if (!outDir.isEmpty()) {
            try {
                saveBlobsToDir(blobs, branchIdentifiers, outDir, 0);
            } catch (IOException e) {
                System.out.println("[Executor] Failed to save: " + e);
            }
        }
        */
        System.out.println("[Executor] blob length " + blobs.size());
        System.out.println("[Executor] branchList length " + ConcolicBranch.getBranchList().size());

        System.out.println("[Executor] post execution blob length " + ConstraintManager.getGeneratedBlobs().size());
        System.out.println("[Executor] post execption branchList length " + ConcolicBranch.getBranchList().size());


        long after_blob_gen_time = System.currentTimeMillis();

        System.out.println("[Executor] Pre-execution Time: " + (before_main_time - start_time) + " ms");
        System.out.println("[Executor] ConcolicExecution Time: " + (before_constraint_solving_time - before_main_time) + " ms");
        System.out.println("[Executor] Constraint Solving Time: " + (after_constraint_solving_time - before_constraint_solving_time) + " ms");
        System.out.println("[Executor] Blob Genenration Time: " + (after_blob_gen_time - after_constraint_solving_time) + " ms");
        System.out.println("[Executor] Total Time: " + (after_blob_gen_time - start_time) + " ms");
        if (blobs.size() > 0) {
            System.out.println("[Executor] Average Constraint Solving Time: " + ((after_constraint_solving_time - before_constraint_solving_time) / blobs.size()) + " ms");
        }
    }

    public static void invoke_fuzzer(Context context, String languageId, String className, byte[] data) throws Exception {
        Value stringArrayType = context.getBindings(languageId).getMember("[B");
        Value byteArray = stringArrayType.newInstance(data.length);
        for (int i = 0; i < data.length; i++) {
            byteArray.setArrayElement(i, data[i]);
        }
        Value tracingTargetClass = context.getBindings(languageId).getMember(className);
        String fuzzerInitialize = "fuzzerInitialize/()V";
        if (tracingTargetClass.hasMember(fuzzerInitialize)) {
            System.out.println("[Executor] fuzzerInitialize()");
            tracingTargetClass.invokeMember(fuzzerInitialize);
        } else if (tracingTargetClass.hasMember("super") && tracingTargetClass.getMember("super").hasMember(fuzzerInitialize)) {
            System.out.println("[Executor] super.fuzzerInitialize()");
            tracingTargetClass.getMember("super").invokeMember(fuzzerInitialize);
        }
        String fuzzerTestOneInputBA = "fuzzerTestOneInput/([B)V";
        String fuzzerTestOneInputFDP = "fuzzerTestOneInput/(Lcom/code_intelligence/jazzer/api/FuzzedDataProvider;)V";
        if (tracingTargetClass.hasMember(fuzzerTestOneInputBA)) {
            System.out.println("[Executor] " + fuzzerTestOneInputBA);
            tracingTargetClass.invokeMember(fuzzerTestOneInputBA, byteArray);
        } else if (tracingTargetClass.hasMember(fuzzerTestOneInputFDP)) {
            System.out.println("[Executor] " + fuzzerTestOneInputFDP);
            Value fdpImpl = context.getBindings(languageId).getMember("com.code_intelligence.jazzer.driver.FuzzedDataProviderImpl");
            Value fdp = fdpImpl.invokeMember("withJavaData/([B)Lcom/code_intelligence/jazzer/driver/FuzzedDataProviderImpl;", byteArray);
            tracingTargetClass.invokeMember(fuzzerTestOneInputFDP, fdp);
        } else {
            System.out.println("[Executor] Entry method not found");
        }
    }
}
