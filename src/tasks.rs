use celery::{prelude::*, Celery};
use std::sync::Arc;

use crate::task::Task;

#[celery::task(time_limit = 10)]
pub async fn add(id: String, x: i32, y: i32) -> TaskResult<i32> {
    info!("adding {} + {}", x, y);
    let result = x + y;
    Ok(AddTask::new(id)
        .store_result(result)
        .await
        .expect("store_result"))
}

pub struct AddTask {
    pub id: String,
}

impl AddTask {
    pub fn new(id: impl ToString) -> Self {
        Self { id: id.to_string() }
    }
}

impl super::task::Task for AddTask {
    type Args = (i32, i32);
    type Result = i32;

    fn task_id(&self) -> &str {
        &self.id
    }

    async fn start(arg: Self::Args) -> eyre::Result<Self> {
        let id = uuid::Uuid::new_v4();
        Self::send(add::new(id.to_string(), arg.0, arg.1)).await?;
        Ok(Self { id: id.to_string() })
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
