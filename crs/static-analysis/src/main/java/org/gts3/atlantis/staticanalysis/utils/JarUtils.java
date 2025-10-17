package org.gts3.atlantis.staticanalysis.utils;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import static org.gts3.atlantis.staticanalysis.utils.LogLabel.LOG_ERROR;

/**
 * Utility class for working with JAR files.
 *
 * This class provides methods to extract information from JAR files,
 * such as listing the class names contained within a JAR file.
 */
public class JarUtils {
    /**
     * Gets a list of fully qualified class names from a JAR file.
     *
     * This method uses the 'jar' command-line tool to extract the list of class files
     * from the JAR file, and converts the file paths to fully qualified class names.
     * For example, "com/example/MyClass.class" becomes "com.example.MyClass".
     *
     * @param jarPath The path to the JAR file
     * @return A list of fully qualified class names contained in the JAR file,
     *         or an empty list if the JAR file does not exist or cannot be read
     */
    public static List<String> getClassNames(Path jarPath) {
        List<String> classNames = new ArrayList<>();

        if (!jarPath.toFile().exists()) {
            return classNames;
        }

        String[] command = {
                "jar",
                "tf",
                jarPath.toString()
        };

        try {
            // Run jar tf <jarPath>
            Process p = Runtime.getRuntime().exec(command);

            try (BufferedReader reader = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                for (String line : reader.lines().toList()) {
                    if (line.endsWith(".class")) {
                        classNames.add(line.substring(0, line.length()-6).replace('/', '.'));
                    }
                }
            }
            p.waitFor();

        } catch (IOException | InterruptedException e) {
            System.out.println(LOG_ERROR + "Failed to get classes from " + jarPath);
        }

        return classNames;
    }
}
