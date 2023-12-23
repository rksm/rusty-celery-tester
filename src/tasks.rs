use celery::{prelude::*, Celery};
use std::sync::Arc;

#[celery::task(time_limit = 10, name = "add")]
pub async fn add(x: i32, y: i32) -> TaskResult<i32> {
    tokio::time::sleep(std::time::Duration::from_secs(1)).await;
    info!("adding {} + {}", x, y);
    Ok(x + y)
}

pub async fn app() -> Result<Arc<Celery>, celery::error::CeleryError> {
    celery::app!(
        broker = RedisBroker { std::env::var("REDIS_ADDR").unwrap() },
        backend = RedisBackend { std::env::var("REDIS_ADDR").unwrap() },
        tasks = [add],
        task_routes = [
            "*" => "celery",
        ],
    )
    .await
}
