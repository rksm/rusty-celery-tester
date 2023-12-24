#[macro_use]
extern crate tracing;

mod task_failure;
mod tasks;

use clap::{Parser, ValueEnum};

#[derive(Parser)]
struct Args {
    #[clap(subcommand)]
    command: Command,
}

#[derive(Parser)]
enum Command {
    Worker(WorkerArgs),
    Client(ClientArgs),
}

#[derive(Parser)]
struct WorkerArgs {}

#[derive(Parser)]
struct ClientArgs {
    #[clap(value_enum, value_delimiter = ',')]
    task: Vec<ClientTask>,
}

#[derive(Debug, Clone, Copy, ValueEnum)]
enum ClientTask {
    #[clap(name = "add")]
    Add,
    #[clap(name = "expected_failure")]
    ExpectedFailure,
    #[clap(name = "unexpected_failure")]
    UnexpectedFailure,
    #[clap(name = "task_with_timeout")]
    TaskWithTimeout,
}

#[tokio::main]
async fn main() {
    color_eyre::install().expect("color_eyre");
    tracing_subscriber::fmt::init();

    run(Args::parse()).await;
}

async fn run(args: Args) {
    match args.command {
        Command::Worker(args) => {
            worker::run(args).await;
        }
        Command::Client(args) => {
            client::run(args).await;
        }
    }
}

mod worker {
    use super::tasks;
    use super::WorkerArgs;

    pub async fn run(_args: WorkerArgs) {
        let app = tasks::app().await.expect("app");
        app.consume_from(&["celery"]).await.expect("consume_from");
    }
}

mod client {

    use celery::prelude::*;

    use super::tasks;
    use super::ClientArgs;

    pub async fn run(args: ClientArgs) {
        let app = tasks::app().await.expect("app");
        println!("RUNNING TASK {:?}", args.task);
        for task in &args.task {
            match task {
                crate::ClientTask::Add => {
                    let task = tasks::add::new(1, 2);
                    let result = app.send_task(task).await.expect("send_task");
                    assert_eq!(3, result.get().fetch().await.unwrap());
                }

                crate::ClientTask::ExpectedFailure => {
                    let task = tasks::expected_failure::new();
                    let result = app.send_task(task).await.expect("send_task");
                    let result = result.get().fetch().await;

                    match result {
                        Err(CeleryError::TaskError(TaskError {
                            kind: TaskErrorType::Expected,
                            ..
                        })) => {
                            info!("expected error from rust")
                        }

                        Err(CeleryError::TaskError(TaskError {
                            kind: TaskErrorType::Other,
                            exc_traceback: Some(tb),
                            ..
                        })) if tb.contains("Exception: expected") => {
                            info!("expected error from python")
                        }

                        _ => panic!("unexpected error: {:?}", result),
                    }
                }

                crate::ClientTask::UnexpectedFailure => {
                    let task = tasks::unexpected_failure::new();
                    let result = app.send_task(task).await.expect("send_task");
                    let result = result.get().fetch().await;

                    match result {
                        Err(CeleryError::TaskError(TaskError {
                            kind: TaskErrorType::Unexpected,
                            ..
                        })) => {
                            info!("expected error from rust")
                        }

                        Err(CeleryError::TaskError(TaskError {
                            kind: TaskErrorType::Other,
                            exc_traceback: Some(tb),
                            ..
                        })) if tb.contains("Exception: unexpected") => {
                            info!("unexpected error from python")
                        }

                        _ => panic!("totally unexpected error: {:?}", result),
                    }
                }

                crate::ClientTask::TaskWithTimeout => {
                    let task = tasks::task_with_timeout::new();
                    let result = app.send_task(task).await.expect("send_task");
                    let result = result.get().fetch().await;
                    match result {
                        Err(CeleryError::TaskError(TaskError {
                            kind: TaskErrorType::Other,
                            exc_type: ty,
                            ..
                        })) if ty == "TimeLimitExceeded" || ty == "SoftTimeLimitExceeded" => {
                            info!("timeout error from python")
                        }

                        _ => panic!("totally unexpected error: {:?}", result),
                    }
                }
            }
        }
        println!("TASK {:?} DONE", args.task);
    }
}
