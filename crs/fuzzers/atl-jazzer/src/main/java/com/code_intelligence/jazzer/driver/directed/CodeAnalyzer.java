/*
 * Copyright 2025 Code Intelligence GmbH
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.code_intelligence.jazzer.driver.directed;

import java.io.File;
import java.util.*;
import soot.*;
import soot.options.Options;

/** Singleton class for loading and analyzing classes using Soot. */
public class CodeAnalyzer {
  private static CodeAnalyzer instance;
  private String sootPath;

  /**
   * Filters the sootPath to only include existing paths. Splits the path by the path separator,
   * checks if each path exists, and reconstructs the path with only the existing paths.
   *
   * @param path The original sootPath to filter
   * @return The filtered sootPath containing only existing paths
   */
  private String filterExistingSootPaths(String path) {
    if (path == null || path.isEmpty()) {
      return "";
    }

    // Split the sootPath by the path separator
    String[] paths = path.split(File.pathSeparator);

    // Filter to only include existing paths
    List<String> existingPaths = new ArrayList<>();
    for (String p : paths) {
      if (new File(p).exists()) {
        existingPaths.add(p);
      }
    }

    // Reconstruct the sootPath with only the existing paths
    return String.join(File.pathSeparator, existingPaths);
  }

  /**
   * Private constructor to prevent direct instantiation.
   *
   * @param sootPath The Soot classpath
   */
  private CodeAnalyzer(String sootPath) {
    this.sootPath = filterExistingSootPaths(sootPath);
  }

  /**
   * Initializes the CodeAnalyzer singleton with the given Soot classpath. This method must be
   * called once before using getInstance().
   *
   * @param sootPath The Soot classpath
   */
  public static synchronized void init(String sootPath) {
    if (instance == null) {
      instance = new CodeAnalyzer(sootPath);
      instance.initialize();
    }
  }

  /** Initializes Soot with the classpath. */
  private void initialize() {
    // Reset Soot's global state
    G.reset();

    // Set Soot options
    Options.v()
        .set_keep_line_number(
            true); // Only keep line numbers, not bytecode offsets (changed due to instrumentation)
    Options.v().set_soot_classpath(sootPath);
    Options.v().set_prepend_classpath(true);
    Options.v().set_allow_phantom_refs(true);
    Options.v().set_whole_program(false); // We're not doing whole-program analysis
    Options.v().set_no_bodies_for_excluded(true); // Don't load method bodies for excluded classes
    Options.v().set_app(true); // Process application classes
    Options.v().set_output_format(Options.output_format_none);
    Options.v().set_ignore_classpath_errors(true); // Ignore classpath errors
    // Options.v().set_exclude(List.of("java.*", "org.*", "jdk.*"));  // ToDo: Review this list
  }

  /**
   * Gets the singleton instance of CodeAnalyzer. The init(String sootPath) method must be called
   * once before using this method.
   *
   * @return The singleton instance
   * @throws IllegalStateException if init() has not been called
   */
  public static synchronized CodeAnalyzer getInstance() {
    if (instance == null) {
      throw new IllegalStateException(
          "CodeAnalyzer has not been initialized. Call init(sootPath) first.");
    }
    return instance;
  }

  /**
   * Loads a class using Soot.
   *
   * @param className The name of the class to load
   */
  public SootClass loadClass(String className) {
    // Replace '/' with '.' in the class name
    className = className.replace('/', '.');
    Scene.v().forceResolve(className, SootClass.BODIES);
    SootClass sootClass = Scene.v().loadClass(className, SootClass.BODIES);

    boolean resolvingDone = Scene.v().doneResolving();
    Scene.v().setResolving(false);
    Scene.v().loadNecessaryClasses();
    Scene.v().setResolving(resolvingDone);

    return sootClass;
  }
}
