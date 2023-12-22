use celery::{prelude::*, Celery};
use std::sync::Arc;

#[celery::task(time_limit = 10, name = "add")]
pub async fn add(x: i32, y: i32) -> TaskResult<i32> {
    info!("adding {} + {}", x, y);
    Ok(x + y)
}

pub struct AddTask {
    pub id: String,
}

impl super::task::Task for AddTask {
    type Args = (i32, i32);
    type Result = i32;

    fn task_id(&self) -> &str {
        &self.id
    }

    async fn start(arg: Self::Args) -> eyre::Result<Self> {
        let result = Self::send(add::new(arg.0, arg.1)).await?;
        Ok(Self { id: result.task_id })
    }
}

pub async fn app() -> Result<Arc<Celery>, celery::error::CeleryError> {
    celery::app!(
        // broker = AMQPBroker { std::env::var("AMQP_ADDR").unwrap() },
        broker = RedisBroker { std::env::var("REDIS_ADDR").unwrap() },
        tasks = [add],
        task_routes = [
            "*" => "celery",
        ],
    )
    .await
}
