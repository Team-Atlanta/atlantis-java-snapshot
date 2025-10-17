use std::{
    borrow::Cow,
    fmt::Debug,
    hash::{Hash, Hasher},
    ops::Deref,
    sync::Mutex,
    path::PathBuf,
    cell::RefCell,
    rc::Rc,
};

use libafl::{
    Error,
    executors::ExitKind,
    inputs::{Input, BytesInput},
    observers::{MapObserver, Observer, TimeObserver},
    state::{HasCorpus, Stoppable},
};
use libafl_bolts::{AsIter, HasLen, Named};
use crate::options::ArtifactPrefix;
use num_traits::Bounded;
use serde::{Deserialize, Serialize};

/// An observer that dumps the input as a crash if an execution contains a
/// finding as deemed by Jazzer.
#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct JazzerFindingObserver {
    artifact_prefix: ArtifactPrefix,
}

fn jazzer_finding_callback() {
    // Jazzer assumes we are going to dump the current unit during this callback.
    // It kills the execution immediately after.
    let dump_data = DUMP_DATA.lock().unwrap().clone();

    if let Some(dump_data) = dump_data {
        eprintln!("[libafl] Received jazzer death callback! Dumping corpus as crash to {}",
            dump_data.output_path.display());
        dump_data.input.to_file(dump_data.output_path).expect("Unable to save crash corpus");
    } else {
        eprintln!("[libafl] Received jazzer death callback! No corpus present though!!!")
    }
}

/// This struct gets stored in static storage so it can be used to dump a jazzer
/// finding as a crash from its death callback.
#[derive(Clone)]
struct JazzerFindingDumpData {
    output_path: PathBuf,
    input: BytesInput,
}

// We need to store this data statically since the jazzer callback will be to a
// plain Rust function. And to use static storage safely in Rust we need to
// guard it with a mutex.
static DUMP_DATA: Mutex<Option<JazzerFindingDumpData>> = Mutex::new(None);

impl JazzerFindingObserver {
    pub fn new(artifact_prefix: ArtifactPrefix) -> Self {
        if libafl_targets::has_jazzer_death_callback() {
            libafl_targets::register_jazzer_death_callback(jazzer_finding_callback);
        }
        Self {
            artifact_prefix
        }
    }
}

impl Named for JazzerFindingObserver {
    fn name(&self) -> &Cow<'static, str> {
        static NAME: Cow<'static, str> = Cow::Borrowed("jazzer-finding");
        &NAME
    }
}

impl<S> Observer<BytesInput, S> for JazzerFindingObserver
where
    S: HasCorpus<BytesInput>
{
    fn pre_exec(&mut self, _state: &mut S, input: &BytesInput) -> Result<(), Error> {
        // File path logic yoinked from LibfuzzerCrashCauseFeedback
        let base = input.generate_name(None);
        let file_path = self.artifact_prefix.dir().join(format!(
            "{}crash-{base}",
            self.artifact_prefix.filename_prefix()
        ));

        let dump_data = JazzerFindingDumpData {
            output_path: file_path,
            input: input.clone(),
        };

        // Lock and write.
        {
            *DUMP_DATA.lock().unwrap() = Some(dump_data);
        }

        Ok(())
    }
}


/// An observer that stops the fuzzer if requested by Jazzer.
#[derive(Debug, Serialize, Deserialize, Clone, Default)]
pub struct JazzerFuzzerStoppingObserver {
    stop: Rc<RefCell<bool>>,
}

impl JazzerFuzzerStoppingObserver {
    pub fn new() -> Self {
        Self {
            stop: Rc::new(RefCell::new(false)),
        }
    }

    pub fn stop(&self) -> Rc<RefCell<bool>> {
        self.stop.clone()
    }
}

impl Named for JazzerFuzzerStoppingObserver {
    fn name(&self) -> &Cow<'static, str> {
        static NAME: Cow<'static, str> = Cow::Borrowed("jazzer-stop");
        &NAME
    }
}

impl<I, S> Observer<I, S> for JazzerFuzzerStoppingObserver
where
    S: Stoppable
{
    fn post_exec(&mut self, state: &mut S, _input: &I, _exit_kind: &ExitKind) -> Result<(), Error> {
        if *self.stop.borrow() {
            state.request_stop();
        }
        Ok(())
    }
}


static INITIAL_SIZE: usize = usize::MAX;
static INITIAL_TIME: u64 = u64::MAX;

pub trait ValueObserver: for<'de> Deserialize<'de> + Serialize + Debug + Named {
    type ValueType: Bounded
        + Default
        + Copy
        + Serialize
        + for<'de> Deserialize<'de>
        + PartialEq
        + Hash
        + Debug
        + 'static;

    fn value(&self) -> &Self::ValueType;

    fn default_value(&self) -> &Self::ValueType;
}

#[derive(Deserialize, Serialize, Debug)]
pub struct MappedEdgeMapObserver<M, O> {
    inner: M,
    name: Cow<'static, str>,
    value_observer: O,
}

impl<M, O> MappedEdgeMapObserver<M, O>
where
    M: MapObserver,
    O: ValueObserver,
{
    pub fn new(obs: M, value_obs: O) -> Self {
        Self {
            name: Cow::from(format!("{}_{}", value_obs.name(), obs.name())),
            inner: obs,
            value_observer: value_obs,
        }
    }
}

impl<M, O> AsRef<Self> for MappedEdgeMapObserver<M, O> {
    fn as_ref(&self) -> &Self {
        self
    }
}

impl<M, O> AsMut<Self> for MappedEdgeMapObserver<M, O> {
    fn as_mut(&mut self) -> &mut Self {
        self
    }
}

impl<M, O> HasLen for MappedEdgeMapObserver<M, O>
where
    M: HasLen,
{
    fn len(&self) -> usize {
        self.inner.len()
    }
}

impl<M, O> Named for MappedEdgeMapObserver<M, O> {
    fn name(&self) -> &Cow<'static, str> {
        &self.name
    }
}

impl<M, O> Hash for MappedEdgeMapObserver<M, O>
where
    M: MapObserver + for<'it> AsIter<'it, Item = M::Entry>,
    O: ValueObserver,
{
    fn hash<H: Hasher>(&self, hasher: &mut H) {
        let initial = self.inner.initial();
        for e in self.inner.as_iter() {
            if *e == initial {
                self.value_observer.default_value().hash(hasher);
            } else {
                self.value_observer.value().hash(hasher);
            }
        }
    }
}

impl<M, O> MapObserver for MappedEdgeMapObserver<M, O>
where
    M: MapObserver + for<'it> AsIter<'it, Item = M::Entry>,
    O: ValueObserver,
{
    type Entry = O::ValueType;

    fn get(&self, idx: usize) -> Self::Entry {
        let initial = self.inner.initial();
        if self.inner.get(idx) == initial {
            *self.value_observer.default_value()
        } else {
            *self.value_observer.value()
        }
    }

    fn set(&mut self, _idx: usize, _val: Self::Entry) {
        unimplemented!("Impossible to implement for a proxy map.")
    }

    fn usable_count(&self) -> usize {
        self.inner.usable_count()
    }

    fn count_bytes(&self) -> u64 {
        self.inner.count_bytes()
    }

    fn initial(&self) -> Self::Entry {
        *self.value_observer.default_value()
    }

    fn reset_map(&mut self) -> Result<(), Error> {
        self.inner.reset_map()
    }

    fn to_vec(&self) -> Vec<Self::Entry> {
        let initial = self.inner.initial();
        let default = *self.value_observer.default_value();
        let value = *self.value_observer.value();
        self.inner
            .as_iter()
            .map(|e| if *e == initial { default } else { value })
            .collect()
    }

    fn how_many_set(&self, indexes: &[usize]) -> usize {
        self.inner.how_many_set(indexes)
    }
}

impl<I, M, O, S> Observer<I, S> for MappedEdgeMapObserver<M, O>
where
    M: Observer<I, S> + Debug,
    O: Observer<I, S> + Debug,
    S: HasCorpus<I>,
{
    fn pre_exec(&mut self, state: &mut S, input: &I) -> Result<(), Error> {
        self.inner.pre_exec(state, input)?;
        self.value_observer.pre_exec(state, input)
    }

    fn post_exec(&mut self, state: &mut S, input: &I, exit_kind: &ExitKind) -> Result<(), Error> {
        self.inner.post_exec(state, input, exit_kind)?;
        self.value_observer.post_exec(state, input, exit_kind)
    }
}

pub struct MappedEdgeMapIter<'it, I, O, T> {
    inner: I,
    initial: T,
    value_obs: &'it O,
}

impl<'it, I, O, T> MappedEdgeMapIter<'it, I, O, T> {
    fn new(iter: I, initial: T, value_obs: &'it O) -> Self {
        Self {
            inner: iter,
            initial,
            value_obs,
        }
    }
}

impl<'it, I, O, R, T> Iterator for MappedEdgeMapIter<'it, I, O, T>
where
    I: Iterator<Item = R>,
    R: Deref<Target = T>,
    T: PartialEq + 'it,
    O: ValueObserver,
{
    type Item = &'it O::ValueType;

    fn next(&mut self) -> Option<Self::Item> {
        self.inner.next().map(|e| {
            (*e == self.initial)
                .then(|| self.value_obs.default_value())
                .unwrap_or_else(|| self.value_obs.value())
        })
    }
}

impl<'it, M, O> AsIter<'it> for MappedEdgeMapObserver<M, O>
where
    M: MapObserver + for<'a> AsIter<'a, Item = M::Entry>,
    M::Entry: 'it,
    O: ValueObserver + 'it,
{
    type Item = O::ValueType;
    type Ref = &'it Self::Item;
    type IntoIter = MappedEdgeMapIter<'it, <M as AsIter<'it>>::IntoIter, O, M::Entry>;

    fn as_iter(&'it self) -> Self::IntoIter {
        let iter = self.inner.as_iter();
        let initial = self.inner.initial();
        MappedEdgeMapIter::new(iter, initial, &self.value_observer)
    }
}

#[derive(Copy, Clone, Serialize, Deserialize, Debug, Default)]
pub struct SizeValueObserver {
    size: usize,
}

impl ValueObserver for SizeValueObserver {
    type ValueType = usize;

    fn value(&self) -> &Self::ValueType {
        &self.size
    }

    fn default_value(&self) -> &Self::ValueType {
        &INITIAL_SIZE
    }
}

impl Named for SizeValueObserver {
    fn name(&self) -> &Cow<'static, str> {
        static NAME: Cow<'static, str> = Cow::Borrowed("size");
        &NAME
    }
}

impl<I, S> Observer<I, S> for SizeValueObserver
where
    I: HasLen,
    S: HasCorpus<I>,
{
    fn pre_exec(&mut self, _state: &mut S, input: &I) -> Result<(), Error> {
        self.size = input.len();
        Ok(())
    }
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct TimeValueObserver {
    time: u64,
    time_obs: TimeObserver,
}

impl TimeValueObserver {
    pub fn new(time_obs: TimeObserver) -> Self {
        Self {
            time: INITIAL_TIME,
            time_obs,
        }
    }
}

impl ValueObserver for TimeValueObserver {
    type ValueType = u64;

    fn value(&self) -> &Self::ValueType {
        &self.time
    }

    fn default_value(&self) -> &Self::ValueType {
        &INITIAL_TIME
    }
}

impl Named for TimeValueObserver {
    fn name(&self) -> &Cow<'static, str> {
        self.time_obs.name()
    }
}

impl<I, S> Observer<I, S> for TimeValueObserver
where
    S: HasCorpus<I>,
{
    fn pre_exec(&mut self, state: &mut S, input: &I) -> Result<(), Error> {
        self.time_obs.pre_exec(state, input)
    }

    fn post_exec(&mut self, state: &mut S, input: &I, exit_kind: &ExitKind) -> Result<(), Error> {
        self.time_obs.post_exec(state, input, exit_kind)?;
        self.time = self
            .time_obs
            .last_runtime()
            .as_ref()
            .map_or(INITIAL_TIME, |duration| {
                u64::try_from(duration.as_micros()).unwrap_or(INITIAL_TIME)
            });
        Ok(())
    }
}

#[derive(Clone, Serialize, Deserialize, Debug)]
pub struct SizeTimeValueObserver {
    value: u64,
    size_obs: SizeValueObserver,
    time_obs: TimeValueObserver,
}

impl SizeTimeValueObserver {
    pub fn new(time_obs: TimeObserver) -> Self {
        Self {
            value: INITIAL_TIME,
            size_obs: SizeValueObserver::default(),
            time_obs: TimeValueObserver::new(time_obs),
        }
    }
}

impl ValueObserver for SizeTimeValueObserver {
    type ValueType = u64;

    fn value(&self) -> &Self::ValueType {
        &self.value
    }

    fn default_value(&self) -> &Self::ValueType {
        &INITIAL_TIME
    }
}

impl Named for SizeTimeValueObserver {
    fn name(&self) -> &Cow<'static, str> {
        static NAME: Cow<'static, str> = Cow::Borrowed("size_time");
        &NAME
    }
}

impl<I, S> Observer<I, S> for SizeTimeValueObserver
where
    S: HasCorpus<I>,
    I: HasLen,
{
    fn pre_exec(&mut self, state: &mut S, input: &I) -> Result<(), Error> {
        self.size_obs.pre_exec(state, input)?;
        self.time_obs.pre_exec(state, input)
    }

    fn post_exec(&mut self, state: &mut S, input: &I, exit_kind: &ExitKind) -> Result<(), Error> {
        self.time_obs.post_exec(state, input, exit_kind)?;
        self.size_obs.post_exec(state, input, exit_kind)?;
        self.value = self
            .time_obs
            .value()
            .saturating_mul(*self.size_obs.value() as u64);
        Ok(())
    }
}
