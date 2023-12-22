#[macro_use]
extern crate tracing;

mod task;
mod task_failure;
mod tasks;

use clap::Parser;

#[derive(Parser)]
struct Args {
    #[clap(subcommand)]
    command: Command,
}

#[derive(Parser)]
enum Command {
    Worker(WorkerArgs),
    Master(MasterArgs),
}

#[derive(Parser)]
struct WorkerArgs {}

#[derive(Parser)]
struct MasterArgs {}

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
        Command::Master(args) => {
            master::run(args).await;
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

mod master {
    use crate::task::Task;

    use super::tasks;
    use super::MasterArgs;

    pub async fn run(_args: MasterArgs) {
        let task = tasks::AddTask::start((1, 2)).await.expect("start");
        let result = task.wait_for_result().await.expect("wait_for_result");
        dbg!(result);
    }
}
