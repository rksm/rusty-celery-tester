#[tokio::main]
async fn main() {
    color_eyre::install().expect("color_eyre");
    tracing_subscriber::fmt::init();

    run().await;
}

async fn run() {
    let con = lapin::Connection::connect(
        "amqp://localhost:5672",
        lapin::ConnectionProperties::default(),
    )
    .await
    .expect("connection error");

    let status = con.status();
    dbg!(status);

    let channel = con.create_channel().await.expect("create_channel");
    // channel.queue_declare(queue, options, arguments)
}
