use celery::task::AsyncResult;
use eyre::Result;
use redis::AsyncCommands;
use redis_macros::FromRedisValue;

use crate::task_failure::CeleryTaskFailure;

#[allow(dead_code)]
#[derive(Debug, serde::Serialize, serde::Deserialize, FromRedisValue)]
pub(crate) struct TaskMeta<T> {
    pub(crate) task_id: String,
    pub(crate) status: String,
    pub(crate) result: T,
    pub(crate) traceback: Option<String>,
    pub(crate) date_done: Option<chrono::NaiveDateTime>,
    // pub(crate) children: Option<Vec<String>>,
}

impl<T> TaskMeta<T> {
    pub(crate) fn success(task_id: impl ToString, result: T) -> Self {
        Self {
            task_id: task_id.to_string(),
            status: "SUCCESS".to_string(),
            result,
            traceback: None,
            date_done: Some(chrono::Utc::now().naive_utc()),
        }
    }
}

impl<T> TaskMeta<T>
where
    T: serde::de::DeserializeOwned,
{
    async fn get(
        task_id: &str,
        redis_backend: &str,
        timeout: std::time::Duration,
        cleanup: bool,
    ) -> eyre::Result<Self> {
        let task_id = format!("celery-task-meta-{task_id}");
        debug!(%task_id, %redis_backend, "getting task result");
        let redis = redis::Client::open(redis_backend)?;
        let mut con = redis.get_async_connection().await?;
        let start = std::time::Instant::now();
        while start.elapsed() < timeout {
            match con.get(&task_id).await {
                Ok(None) => continue,
                Ok(Some(task_result)) => {
                    if cleanup {
                        con.del(&task_id).await?;
                    }
                    return Ok(task_result);
                }
                Err(err) => {
                    match con.get::<'_, _, CeleryTaskFailure>(&task_id).await {
                        Ok(failure) => {
                            return Err(failure.into());
                        }
                        _ => {
                            return Err(err.into());
                        }
                    };
                }
            }
        }
        eyre::bail!("timeout")
    }
}

impl<T> TaskMeta<T>
where
    T: serde::ser::Serialize,
{
    async fn store(self, redis_backend: &str) -> eyre::Result<T> {
        let task_id = format!("celery-task-meta-{}", self.task_id);
        let redis = redis::Client::open(redis_backend)?;
        let mut con = redis.get_async_connection().await?;
        con.set(&task_id, &serde_json::to_string(&self)?).await?;
        Ok(self.result)
    }
}

pub trait Task: Sized {
    type Args;
    type Result: serde::ser::Serialize
        + serde::de::DeserializeOwned
        + redis::ToRedisArgs
        + Send
        + Sync;

    fn task_id(&self) -> &str;

    fn cleanup(&self) -> bool {
        true
    }

    fn wait_duration(&self) -> std::time::Duration {
        std::time::Duration::from_secs(10)
    }

    async fn start(args: Self::Args) -> Result<Self>;

    async fn send<T>(task_sig: celery::task::Signature<T>) -> Result<AsyncResult>
    where
        T: celery::task::Task,
    {
        let app = super::tasks::app().await?;
        debug!("submitting task");
        Ok(app.send_task(task_sig).await?)
    }

    async fn store_result(&self, result: Self::Result) -> Result<Self::Result> {
        debug!(task_id = self.task_id(), "storing task result");
        TaskMeta::success(self.task_id(), result)
            .store(&std::env::var("REDIS_ADDR")?)
            .await
    }

    async fn wait_for_result(self) -> Result<Self::Result> {
        let task_id = self.task_id();

        debug!(%task_id, "waiting for task result");

        let task_result = TaskMeta::<Self::Result>::get(
            task_id,
            &std::env::var("REDIS_ADDR")?,
            self.wait_duration(),
            self.cleanup(),
        )
        .await?;

        debug!(status = %task_result.status, "task result status");

        Ok(task_result.result)
    }
}
