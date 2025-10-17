/*******************************************************************************
 * Copyright (c) 2009, 2025 Mountainminds GmbH & Co. KG and Contributors
 * This program and the accompanying materials are made available under
 * the terms of the Eclipse Public License 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0
 *
 * SPDX-License-Identifier: EPL-2.0
 *
 * Contributors:
 *    Marc R. Hoffmann - initial API and implementation
 *
 *******************************************************************************/
package org.jacoco.cli.internal.commands;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.jacoco.cli.internal.Command;
import org.jacoco.core.internal.analysis.Instruction;
import org.jacoco.core.analysis.Analyzer;
import org.jacoco.core.analysis.CoverageBuilder;
import org.jacoco.core.analysis.IClassCoverage;
import org.jacoco.core.analysis.IMethodCoverage;
import org.jacoco.core.data.ExecutionDataStore;
import org.jacoco.core.tools.ExecFileLoader;
import org.jacoco.report.DirectorySourceFileLocator;
import org.jacoco.report.FileMultiReportOutput;
import org.jacoco.report.IReportVisitor;
import org.jacoco.report.ISourceFileLocator;
import org.jacoco.report.MultiReportVisitor;
import org.jacoco.report.MultiSourceFileLocator;
import org.kohsuke.args4j.Argument;
import org.kohsuke.args4j.Option;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.jacoco.core.internal.analysis.ClassAnalyzer;
import org.jacoco.core.analysis.ICounter;
/**
 * The <code>execinfo</code> command.
 */
public class Partly extends Command {

	@Argument(usage = "list of JaCoCo *.exec files to read", metaVar = "<execfiles>")
	List<File> execfiles = new ArrayList<File>();

	@Option(name = "--classfiles", usage = "location of Java class files", metaVar = "<path>", required = true)
	List<File> classfiles = new ArrayList<File>();

	@Override
	public String description() {
		return "Read exec file and print the bcis of the not fully covered branches";
	}

	@Override
	public int execute(final PrintWriter out, final PrintWriter err)
			throws IOException {
		final ExecFileLoader loader = loadExecutionData(out);
		final Collection<IClassCoverage> classes = analyze(loader.getExecutionDataStore(),
				out);
		for (final IClassCoverage classCoverage : classes) {
			// out.printf("[INFO] %s\n", classCoverage.getName());
			for (final IMethodCoverage methodCoverage : classCoverage.getMethods()) {
				// out.printf("[INFO] %s\n", methodCoverage.getName());
			}
		}
		return 0;
	}

	private ExecFileLoader loadExecutionData(final PrintWriter out)
			throws IOException {
		final ExecFileLoader loader = new ExecFileLoader();
		if (execfiles.isEmpty()) {
			// out.println("[WARN] No execution data files provided.");
		} else {
			for (final File file : execfiles) {
				// out.printf("[INFO] Loading execution data file %s.%n",
				// 		file.getAbsolutePath());
				loader.load(file);
			}
		}
		return loader;
	}

	private boolean isInvalid(final File f) {
		if (f.isDirectory()) {
			return true;
		}
		if (!f.getName().endsWith(".class")) {
			return true;
		}
		return false;
	}

	private Collection<IClassCoverage> analyze(final ExecutionDataStore data,
			final PrintWriter out) throws IOException {
		final CoverageBuilder builder = new CoverageBuilder();
		final Analyzer analyzer = new Analyzer(data, builder);

		for (int i = 0; i < classfiles.size(); i++) {
			File f = classfiles.get(i);
			if (f.isDirectory()) {
				for (File file : f.listFiles()) {
					classfiles.add(file);
				}
				continue;
			}
			if (isInvalid(f)) {
				continue;
			}

			try {
				analyzer.analyzeAll(f);
			} catch (Exception e) {
				System.err.println("ERR|" + f.getAbsolutePath());
				continue;
			}
			
			if (analyzer.getUsedClassAnalyzer() == null) {
				// System.out.println("No class analyzer found for " + f.getAbsolutePath());
				continue;
			}
			Map<String, Map<String, Map<AbstractInsnNode, Instruction>>> methodInstructions = analyzer.getUsedClassAnalyzer().getMethodInstructions();
			for (String methodName : methodInstructions.keySet()) {
				for (String methodDesc : methodInstructions.get(methodName).keySet()) {
					for (Map.Entry<AbstractInsnNode, Instruction> entry : methodInstructions.get(methodName).get(methodDesc).entrySet()) {
						AbstractInsnNode insn = entry.getKey();
						Instruction instruction = entry.getValue();

						String name = methodName + methodDesc;
						int status = instruction.getBranchCounter().getStatus();
						if (status == ICounter.PARTLY_COVERED) {
							System.out.println("CLS|" + f.getAbsolutePath());
							System.out.println("BCH|" + name + ":" + instruction.getByteOffset());
						}
					}
				}
			}
		}
		return builder.getClasses();
	}

}
