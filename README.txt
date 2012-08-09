This is SCOMP, the Spreadsheet COMPiler.

scomp is a research tool that reads machine-readable results files from
simulations and combines them in programmable ways (with user-specified
formulas) to produce spreadsheets and plots as output. It was written with
computer architecture research in mind (in which a ``run'' consists of several
simulator knob configurations run with a common set of benchmarks), though it
may be useful in other, as-yet-unforeseen, ways as well.

scomp is released under the GNU GPL, version 2 only. It is copyright (c)
2011-2012 Chris Fallin <cfallin@c1f.net>.

====== background: computer architecture simulation data ======

scomp is designed to parse the results of ``simulations'' which are performed
in the course of computer architecture research. Most research in computer
architecture is performed using simulators which take (i) a set of knobs, or
configuration parameters, to specify a machine to model, and (ii) a benchmark,
which is a program that runs on the simulator in order to evaluate the
performance of the modeled machine. The simulator executes the benchmark and
produces a set of statistics, or metrics, which represent the behavior of the
modeled machine (for example, the number of cache misses or branch
mispredictions, or cycles taken to execute the benchmark). These metrics are
the ``measurements'' which inform conclusions about the modeled
microarchitecture and allow computer architecture to be a rigorous quantitative
science.

Typically, a researcher proposes a new microarchitectural feature or mechanism
and modifies a simulator and then performs several ``runs'' on a known set of
benchmarks. This results in a matrix of data: for every evaluated machine
configuration, for every evaluated benchmark, there should be a set of metrics
which are the result of one simulation. A researcher is typically interested in
viewing one particular metric (for example, instructions per cycle) for each
benchmark and on average over all benchmarks, on the various configurations.

scomp is designed for this common use-case. It explicitly knows about
``configurations'' and ``benchmarks'' and can load a simulator result file for
each configuration running each benchmark. A set of user-defined formulas is
then evaluated for each such point and merged into the set of metrics loaded
from the simulation data. These formulas can refer to either the same or a
different configuration, but always for the same benchmark. (For example, an
user-defined formula could represent the percent performance gain for each
benchmark from a ``baseline'' configuration to a ``new-proposed''
configuration.)

To install, simply do "sudo ./setup.py" or else "./setup.py
~/my_local_binary_directory", which will install scomp in /usr/local/bin or
~/my_local_binary_directory respectively.

=== Input Format ===

scomp reads "configurations", which are the results of simulator runs over a
common set of benchmarks for a particular set of simulator options. scomp does
not care about the particulars of the simulator, its configuration options, or
how the simulation runs were coordinated; it only expects a particular
directory structure with JSON files.

The directory structure required by scomp is as follows: under a top-level data
directory, each configuration has a subdirectory. Under each configuration
subdirectory, further subdirectories should exist for each benchmark. In each
benchmark directory, the file "sim.out" must exist as a JSON file (other files
can also exist, and scomp will ignore them).

So, for example, if we were to simulate a baseline system and a system with the
Foobar widget, both for 100M instructions, we might have the following
structure:

 data/
    100M_base/
         400.perlbench/
              sim.out       <--- scomp only cares about this file
              condor_stdout.txt
              condor_stderr.txt
              condor_log.txt
              auxiliary_log.txt
         401.bzip2/
              sim.out
    100M_foobar/
         400.perlbench/
              sim.out/
         ...

Each 'sim.out' file should have the following data structure. The top-level object should be a dictionary, and each key in the dictionary should be a stat name. Each value associated with a stat can have one of several formats: it can either be a float or int directly, or it can be a dictionary itself, in which case scomp takes the 'avg' key in this sub-dictionary, or it can be a single-element array of either of these types. (scomp reserves the right to support other stat formats in the future, and/or to extract special-purpose information from particular stat types, such as distributions.) A sample simulator output file might be:

 {
    "cycles": 100000000,
    "foobar_events": [123400],
    "insns_retired": [67012345]
 }

=== Scompfile ===

scomp is controlled by a specification in a domain-specific language, called a
Scompfile, that indicates data directories, statistics to gather, defines
composite metrics, and specifies what spreadsheets to produce. We will give an
example Scompfile here, and walk through its sections one at a time.

Note that a Scompfile is a JSON file. At the top level, it is a dictionary, and
each section of directives is given as a particular data structure under a key.
Most data structures are built as nested lists.


 {
     "configs": [
         ["100M_base", "base"],
         ["100M_foobar", "foobar"]
     ],
 
     "stats": [
         "cycles",
         "core_insn_fetched",
         "core_insn_retired",
         "dram_latency",
         "foobar_*"
     ],
 
     "exprs": [
         ["*", [
                 ["!IPC", "core_insn_retired/cycles"],
                 ["!IPC_improvement", "(!IPC-base.!IPC)/base.!IPC"]
         ]],
         ["foobar", [
                 ["!foobar_rate", "(foobar_event1+foobar_event2)/cycles"]
         ]]
     ],
 
     "sheets": [
         ["data_all", "full", ["*"]],
         ["summary", "benchsummary",
             ["base.!IPC", "foobar.!IPC",
              "foobar.!IPC_improvement", "!foobar_rate"]]
     ]
 }

==== Input Specification: Configs and Stats ====

The first part of the Scompfile above defines where the simulation output data
can be found. The Scompfile specifies a set of configs (a simulation run over
the common set of benchmarks for a particular set of simulator parameters), and
a set of stats to collect from each benchmark in each config.

First, the "configs" key gives a list of tuples, each of which specifies one
config. The first element in each tuple is a string that names the config
subdirectory; e.g., the first config in the sample Scompfile would locate its
data under "data/100M_base/". The second string in each tuple gives a short
name for that config by which the rest of the Scompfile can refer to the
config.

Second, the "stats" key gives a list of stats, as defined in each simulator
output file, that should be extracted. Note that wildcards can be used: e.g.,
in this sample, "foobar_*" specifies that all stats beginning with "foobar_"
will be loaded from results files and included in output.

==== Composite Stats: Expressions ====

Once scomp has the data for each benchmark in each config, it processes
"expressions" to define composite statistics for each benchmark. These
expressions are a form of spreadsheet/dataflow programming: each expression can
depend on other expressions in turn, and scomp will evaluate expressions until
all unknowns are resolved. The ability to compute arbitrary composite
statistics is scomp's most powerful feature.

A few principles govern how scomp expressions work:

1. Each expression is named starting with "!" (bang), so that composite
statistics are distinguished from raw statistics (those statistics extracted
from simulator output files). In the sample above, "!IPC" is a composite
statistic, while "cycles" is a raw statistic.

2. Composite and raw statistics are computed for each benchmark independently.
However, expressions can refer to any configuration for a given benchmark. In
the example above, "!IPC_improvement" is computed for every configuration of
every benchmark relative to the "base" config. One can think of scomp as
constructing a separate mini-spreadsheet for each benchmark, where each
configuration of the benchmark has one row, each statistic has one column, and
expressions can refer to any row/column.

3. Composite and raw statistics can be referred to either with a short name
(e.g., simply "!IPC") or a long name (e.g., "foobar.!IPC"). In the former case,
the name refers to the "current" configuration (e.g., the expression
"core_insns_retired/cycles" evaluated at a given configuration will load the
named statistics for that configuration). In the latter case, the statistic is
loaded from the named configuration.

A scomp expression is actually a full Python expression. scomp begins
evaluation by loading all raw statistics, setting all composite statistics to
zero, and then using a worklist-based dataflow evaluation algorithm to evaluate
expressions and their dependent expressions until a fixpoint is reached. (This
operation is very similar to a spreedsheat evaluation.)

Expressions are specified in a list of clauses under the "exprs" key. Each
clause begins with a string, which can contain wildcards, that specifies to
which configurations the following expressions will apply. In the sample above,
"*" indicates that the first two composite metrics are defined for all
configurations, while the last "!foobar_rate" is defined only for the "foobar"
configuration". The second element of each clause is a list of expression
tuples, where each tuple contains the name of the expression first, followed by
the expression's definition second.

==== Output Specification: Sheets ====

Finally, the "sheets" key specifies what spreadsheets (really, CSV files) scomp
should produce. Each clause specifies three elements: the sheet name, the type,
and a list of elements. Two types are supported: "full" and "benchsummary".

A "full" sheet contains one row per benchmark per configuration. Each benchmark
has a cluster of configurations in their rows, followed by a blank row,
followed by the next benchmark. The list in the sheet specification provides a
list of configurations to output.

A "benchsummary" sheet contains one row per benchmark, with only the given
statistics included, one per column. This type of sheet is useful e.g. to
produce source data for plots, and provides a more condensed view.

=== Producing Plots ===

TODO

=== Running scomp ===

scomp can be invoked in two ways. Either the data directory (input) and CSV
sheet directory and plot directory (output) can be specified explicitly:

 scomp Scompfile data/ sheets/ plots/

or one can simply do:

 scomp Scompfile

Furthermore, scomp can replace arbitrary expressions in scompfiles with
substituted values, for example to have a parameterized scompfile. This is done
with the ``-var'' flag:

  scomp -var BASECONFIG=system1 -var MYVAR=foobar Scompfile

=== Real-World Examples ===

The following is a real-world example of a Scompfile (from the [[Skipahead]] project):

 {
     "configs": [
         ["100M_base", "base"],
         ["100M_ra_prefcache", "RA"],
         ["100M_pref_base_prefcache", "pref"],
         ["100M_filtra_prefcache", "filtRA"],
         ["100M_filtra_condbr_prefcache", "filtRAC"],
         ["100M_sa4_prefcache", "SA4"],
         ["100M_sa5_prefcache", "SA5"],
         ["100M_sa5_multi_prefcache", "SA5multi"]
     ],
 
     "stats": [
         "cycles",
         "core_insn_fetched",
         "core_insn_retired",
         "core_macroinsn_retired",
         "dram_latency",
         "prefcache_*",
         "ra_*",
         "filtra_*",
         "l2_*",
         "sa_*"
     ],
 
     "exprs": [
         ["*", [
                 ["!IPC", "core_macroinsn_retired/cycles"],
                 ["!coverage", "prefcache_useful/base.l2_miss"],
                 ["!accuracy", "prefcache_useful/prefcache_insert"],
                 ["!extra", "ra_insn_retired/core_insn_retired"],
                 ["!imp", "(!IPC-base.!IPC)/base.!IPC"]
         ]],
 
         ["filtRA*", [
                 ["!fracInsns", "ra_insn_retired/RA.ra_insn_retired"],
                 ["!fracPerf", "(!IPC-base.!IPC)/(RA.!IPC-base.!IPC)"],
                 ["!fracCoverage", "!coverage/RA.!coverage"],
                 ["!fracAccuracy", "!accuracy/RA.!accuracy"]
          ]]
     ],
 
     "sheets": [
         ["data_all", "full", ["*"]],
         ["data_RA", "full", ["base", "pref", "RA", "filtRA", "filtRAC"]],
         ["summary", "benchsummary",
             ["pref.!imp", "pref.!coverage", "pref.!accuracy", "pref.!extra",
              "RA.!imp", "RA.!coverage", "RA.!accuracy", "RA.!extra",
              "filtRA.!imp", "filtRA.!coverage", "filtRA.!accuracy", "filtRA.!extra",
              "filtRA.!fracInsns", "filtRA.!fracPerf", "filtRA.!fracCoverage", "filtRA.!fracAccuracy",
              "filtRAC.!imp", "filtRAC.!coverage", "filtRAC.!accuracy", "filtRAC.!extra",
              "filtRAC.!fracInsns", "filtRAC.!fracPerf", "filtRAC.!fracCoverage", "filtRAC.!fracAccuracy"
              ]]
     ],
 
     "plots": [
         ["ipc", {
                     "style": "groupbar",
                     "configs": ["*"],
                     "y": "!IPC",
                     "avg": ["arithmetic"]
                 }],
        ["coverage", {
                     "style": "groupbar",
                     "configs": ["RA", "pref", "filtRA", "filtRAC", "SA4", "SA5", "SA5multi"],
                     "y": "!coverage",
                     "avg": ["arithmetic"]
                }],
        ["accuracy", {
                     "style": "groupbar",
                     "configs": ["RA", "pref", "filtRA", "filtRAC", "SA4", "SA5", "SA5multi"],
                     "y": "!accuracy",
                     "avg": ["arithmetic"]
                }]
     ]
 }
