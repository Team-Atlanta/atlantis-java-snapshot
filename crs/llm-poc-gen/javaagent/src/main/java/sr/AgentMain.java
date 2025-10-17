package sr;

import com.code_intelligence.jazzer.api.FuzzedDataProvider;
import com.code_intelligence.jazzer.driver.FuzzedDataProviderImpl;
import java.io.IOException;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.HashSet;

public class AgentMain {
    public static void premain(String agentArgs, Instrumentation inst) {
        inst.addTransformer(new ASMTransformer(new HashSet<>(Arrays.asList(agentArgs.split(",")))));
    }

    public static void main(String[] args) {
        if (args.length != 2) {
            System.out.println("Usage: java Main <ClassName> <FileName>");
            return;
        }

        String className = args[0];
        String fileName = args[1];
        byte[] data = null;
        try {
            data = Files.readAllBytes(Paths.get(fileName));
        } catch (IOException e) {
            System.err.println("Failed to read file (" + fileName + ")");
            return;
        }

        Class<?> clazz = null;
        try {
            clazz = Class.forName(className);
        } catch (ClassNotFoundException e) {
            System.err.println("Class Not Found: " + className);
            return;
        }

        try {
            Method m = clazz.getDeclaredMethod("fuzzerInitialize");
            m.setAccessible(true);
            m.invoke(null);
        } catch (Exception e) {}

        String entry_name = "fuzzerTestOneInput";
        try {
            Method m = clazz.getDeclaredMethod(entry_name, byte[].class);
            m.setAccessible(true);
            m.invoke(null, (Object) data);
        } catch (Exception e) {}

        FuzzedDataProviderImpl fuzzedDataProvider = FuzzedDataProviderImpl.withJavaData(data);
        try {
            clazz.getDeclaredMethod(entry_name, FuzzedDataProvider.class).invoke(null, (Object) fuzzedDataProvider);
        } catch (Exception e) {}
    }
}
