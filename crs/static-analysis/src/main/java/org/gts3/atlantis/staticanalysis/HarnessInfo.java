package org.gts3.atlantis.staticanalysis;

import soot.Scene;
import soot.SootClass;
import soot.SootMethod;

import java.sql.Array;
import java.util.List;
import java.util.ArrayList;

import org.gts3.atlantis.staticanalysis.utils.SignatureUtils;

/**
 * Class representing information about a harness.
 */
public class HarnessInfo {
    private String javaHome;
    private String jvmLdLibraryPath;
    private String ldLibraryPath;
    private String binPath;
    private List<String> classpath;
    private String name;
    private String srcPath;
    private String targetClass;
    private String targetMethod;
    private String targetMethodDesc;

    /**
     * Constructor with all fields.
     *
     * @param javaHome The JAVA_HOME path
     * @param jvmLdLibraryPath The JVM_LD_LIBRARY_PATH
     * @param ldLibraryPath The LD_LIBRARY_PATH
     * @param binPath The binary path
     * @param classpath The classpath list
     * @param name The harness name
     * @param srcPath The source path
     * @param targetClass The target class (required)
     * @param targetMethod The target method (required)
     * @param targetMethodDesc The target method descriptor (required)
     * @throws IllegalArgumentException if targetClass or targetMethod is null
     */
    public HarnessInfo(String javaHome, String jvmLdLibraryPath, String ldLibraryPath,
                      String binPath, List<String> classpath, String name,
                      String srcPath, String targetClass, String targetMethod, String targetMethodDesc) {
        if (targetClass == null) {
            throw new IllegalArgumentException("targetClass cannot be null");
        }
        if (targetMethod == null) {
            throw new IllegalArgumentException("targetMethod cannot be null");
        }
        this.javaHome = javaHome;
        this.jvmLdLibraryPath = jvmLdLibraryPath;
        this.ldLibraryPath = ldLibraryPath;
        this.binPath = binPath;
        this.classpath = classpath != null ? classpath : new ArrayList<>();
        this.name = name;
        this.srcPath = srcPath;
        this.targetClass = targetClass;
        this.targetMethod = targetMethod;
        this.targetMethodDesc = targetMethodDesc;
    }

    /**
     * Gets the JAVA_HOME path.
     *
     * @return The JAVA_HOME path
     */
    public String getJavaHome() {
        return javaHome;
    }

    /**
     * Gets the JVM_LD_LIBRARY_PATH.
     *
     * @return The JVM_LD_LIBRARY_PATH
     */
    public String getJvmLdLibraryPath() {
        return jvmLdLibraryPath;
    }

    /**
     * Gets the LD_LIBRARY_PATH.
     *
     * @return The LD_LIBRARY_PATH
     */
    public String getLdLibraryPath() {
        return ldLibraryPath;
    }

    /**
     * Gets the binary path.
     *
     * @return The binary path
     */
    public String getBinPath() {
        return binPath;
    }

    /**
     * Gets the classpath list.
     *
     * @return The classpath list
     */
    public List<String> getClasspath() {
        return classpath;
    }

    /**
     * Gets the harness name.
     *
     * @return The harness name
     */
    public String getName() {
        return name;
    }

    /**
     * Gets the source path.
     *
     * @return The source path
     */
    public String getSrcPath() {
        return srcPath;
    }

    /**
     * Gets the target class.
     *
     * @return The target class
     */
    public String getTargetClass() {
        return targetClass;
    }

    /**
     * Gets the target method.
     *
     * @return The target method
     */
    public String getTargetMethod() {
        return targetMethod;
    }

    /**
     * Gets the target method descriptor.
     *
     * @return The target method descriptor
     */
    public String getTargetMethodDesc() {
        return targetMethodDesc;
    }

    /**
     * Gets the Soot methods that match the target method specification.
     *
     * This method loads the target class and finds all methods that match
     * the target method name and descriptor.
     *
     * @return A list of matching Soot methods
     */
    public List<SootMethod> getSootMethods() {
        List<SootMethod> sootMethods = new ArrayList<>();
        SootClass s = Scene.v().loadClass(targetClass, SootClass.SIGNATURES);
        for (SootMethod method : s.getMethods()) {
            if (method.getName().equals(targetMethod)
                    && (targetMethodDesc == null || SignatureUtils.bytecodeSignature(method).equals(targetMethodDesc))) {
                sootMethods.add(method);
            }
        }
        return sootMethods;
    }

    /**
     * Returns a string representation of this harness information.
     *
     * @return A string containing all the harness information fields
     */
    @Override
    public String toString() {
        return "HarnessInfo{" +
                "javaHome='" + javaHome + '\'' +
                ", jvmLdLibraryPath='" + jvmLdLibraryPath + '\'' +
                ", ldLibraryPath='" + ldLibraryPath + '\'' +
                ", binPath='" + binPath + '\'' +
                ", classpath=" + classpath +
                ", name='" + name + '\'' +
                ", srcPath='" + srcPath + '\'' +
                ", targetClass='" + targetClass + '\'' +
                ", targetMethod='" + targetMethod + '\'' +
                ", targetMethodDesc='" + targetMethodDesc + '\'' +
                '}';
    }
}
