use celery::{prelude::*, Celery};
use std::sync::Arc;

#[celery::task(time_limit = 1, name = "add")]
pub async fn add(x: i32, y: i32) -> TaskResult<i32> {
    info!("adding {} + {}", x, y);
    Ok(x + y)
}

#[celery::task(time_limit = 1, name = "expected_failure", max_retries = 0)]
pub async fn expected_failure() -> TaskResult<i32> {
    Err(TaskError::expected("failure expected".to_string()))
}

#[celery::task(time_limit = 1, name = "unexpected_failure")]
pub async fn unexpected_failure() -> TaskResult<i32> {
    Err(TaskError::unexpected("failure still expected".to_string()))
}

#[celery::task(time_limit = 1, name = "task_with_timeout")]
pub async fn task_with_timeout() -> TaskResult<()> {
    tokio::time::sleep(std::time::Duration::from_secs(2)).await;
    Ok(())
}

pub async fn app() -> Result<Arc<Celery>, celery::error::CeleryError> {
    celery::app!(
        broker = RedisBroker { std::env::var("REDIS_ADDR").unwrap() },
        backend = RedisBackend { std::env::var("REDIS_ADDR").unwrap() },
        tasks = [add, expected_failure, unexpected_failure, task_with_timeout],
        task_routes = [
            "*" => "celery",
        ],
    )
    .await
}
