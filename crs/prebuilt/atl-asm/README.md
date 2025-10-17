# ASM

ASM is an all purpose Java bytecode manipulation and analysis framework. It can
be used to modify existing classes or to dynamically generate classes, directly
in binary form. ASM provides some common bytecode transformations and analysis
algorithms from which custom complex transformations and code analysis tools can
be built. ASM offers similar functionality as other Java bytecode frameworks,
but is focused on [performance](https://asm.ow2.io/performance.html). Because it
was designed and implemented to be as small and as fast as possible, it is well
suited for use in dynamic systems (but can of course be used in a static way
too, e.g. in compilers).

## Building the Project

To build the project, you need to have [Java 11+](https://openjdk.java.net)
installed on your system. You can build the project by running the following
command:

```shell
./gradle/gradlew clean build
```

After the build is complete, you can find the compiled JAR files in the
corresponding `build/libs` directory of each submodule.

To run only the project tests, you can use the following command:

```shell
./gradle/gradlew test
```

## How to Contribute

To contribute to the ASM project fork this repository
on [GitLab](https://gitlab.ow2.org/asm/asm), make changes,
then send us
a [merge request](https://docs.gitlab.com/ee/user/project/merge_requests/creating_merge_requests.html).
We will review your changes and apply them to the `master` branch.
To avoid frustration, before sending us your merge request, please run a full
Gradle build to ensure that your changes do not violate our quality standards:

```shell
./gradle/gradlew clean build
```

All submodules are checked
with [googleJavaFormat](https://github.com/google/google-java-format),
[Checkstyle](https://checkstyle.sourceforge.io)
and [PMD](https://pmd.github.io).

## Reporting Issues

If you encounter any issues with the ASM project, please create a new issue
on the [GitLab issue tracker](https://gitlab.ow2.org/asm/asm/-/issues).

## License

ASM is licensed under the [BSD 3-Clause License](LICENSE.txt).