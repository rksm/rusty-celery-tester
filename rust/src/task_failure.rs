use redis_macros::FromRedisValue;

#[allow(dead_code)]
#[derive(Debug, serde::Deserialize, FromRedisValue)]
pub(crate) struct CeleryTaskFailure {
    pub(crate) status: String,
    pub(crate) result: CeleryTaskFailureResult,
    pub(crate) traceback: Option<String>,
    pub(crate) date_done: Option<chrono::NaiveDateTime>,
    pub(crate) task_id: String,
}

#[allow(dead_code)]
#[derive(Debug, serde::Deserialize, FromRedisValue)]
pub(crate) struct CeleryTaskFailureResult {
    pub(crate) exc_type: String,
    pub(crate) exc_message: CeleryTaskFailureMessagePart,
    pub(crate) exc_module: String,
    pub(crate) exc_cause: Option<String>,
    pub(crate) exc_traceback: Option<String>,
}

#[derive(Debug, serde::Deserialize, FromRedisValue)]
#[serde(untagged)]
pub(crate) enum CeleryTaskFailureMessagePart {
    Text(String),
    List(Vec<CeleryTaskFailureMessagePart>),
    Other(serde_json::Value),
}

impl std::fmt::Display for CeleryTaskFailure {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let Self {
            status,
            result,
            traceback,
            date_done,
            task_id,
        } = self;
        let CeleryTaskFailureResult {
            exc_type,
            exc_message,
            exc_module,
            exc_cause: _,
            exc_traceback,
        } = result;

        write!(f, "Celery task failed task_id={task_id} status={status}")?;
        if let Some(t) = date_done {
            write!(f, " time={t}")?;
        }
        writeln!(f)?;
        writeln!(f, "{exc_type}: {exc_module}")?;
        exc_message.print(f, 0)?;
        if let Some(trace) = exc_traceback {
            writeln!(f, "exc traceback: {trace}")?;
        }
        if let Some(trace) = traceback {
            writeln!(f, "traceback: {trace}")?;
        }
        Ok(())
    }
}

impl std::error::Error for CeleryTaskFailure {}

impl CeleryTaskFailureMessagePart {
    fn print(&self, f: &mut std::fmt::Formatter<'_>, indent: usize) -> std::fmt::Result {
        match self {
            CeleryTaskFailureMessagePart::Text(it) => {
                writeln!(f, "{}{it}", " ".repeat(indent))?;
            }
            CeleryTaskFailureMessagePart::List(it) => {
                for item in it {
                    item.print(f, indent + 2)?;
                }
            }
            CeleryTaskFailureMessagePart::Other(it) => {
                writeln!(f, "{}{it}", " ".repeat(indent))?;
            }
        }
        Ok(())
    }
}
