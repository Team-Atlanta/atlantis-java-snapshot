package com.ammaraskar.tracer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.sun.jdi.connect.VMStartException;

import java.io.IOException;
import java.util.Arrays;

public class Main {

    public static void main(String[] args) throws IOException {
        String classPath = args[0];
        String mainClass = args[1];
        StringBuilder mainClassAndArgs = new StringBuilder(mainClass);
        // Despite the fact that this is called mainClass, it is also used to pass arguments to the debugged program,
        // so it's actually mainClassAndArgs really... add remaining args as quoted strings.
        Arrays.stream(args).skip(2).forEach(arg -> {
            mainClassAndArgs.append(" ").append('"').append(arg).append('"');
        });

        ExecutionTracer tracer = new ExecutionTracer(classPath, mainClassAndArgs.toString());
        try {
            tracer.startExecution();
        } catch (RuntimeException e) {
            if (e.getCause() instanceof VMStartException startException) {
                System.err.println("Encountered VMStartException during execution");
                System.err.println("mainClassAndArgs: " + mainClassAndArgs.toString());
                System.err.println(" -------------------stderr------------------- ");
                startException.process().getErrorStream().transferTo(System.err);
                System.err.println(" -------------------stdout------------------- ");
                startException.process().getInputStream().transferTo(System.err);
                System.err.println(" -------------------------------------------- ");
            }
            throw e;
        }

        TraceResult result = tracer.getBestCandidateForWhereExecutionIsStuck();

        // If the stuck frame is LauncherHelper's checkAndLoadMain, we actually failed to load the main class so
        // that's a problem.
        StackTrace stuckTrace = result.getStuckCandidateTrace();
        StackTraceFrame stuckFrame = stuckTrace.getFrames().get(stuckTrace.getFrames().size() - 1);
        if (stuckFrame.getMethodName().equals("checkAndLoadMain")) {
            System.err.println("Unable to find main class.");
            System.exit(1);
        }

        ObjectMapper mapper = new ObjectMapper().disable(SerializationFeature.INDENT_OUTPUT);
        System.out.println("==== Stuck Frame ====");
        System.out.println(mapper.writeValueAsString(result));
    }

}
