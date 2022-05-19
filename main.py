from monitoring import org, cal, setup, utils

_FIRST_YEAR = 2020


def org_log():
    weeks_dir = setup.create_and_get_week_dir()
    df = org.load_data(week_root=weeks_dir, first_weekday_index=3)
    df = org.process_data(df)

    messages = org.messages_this_week(df)
    print(f"Generated messages: {messages}.")

    image_paths = org.images_this_week(df, path=weeks_dir)
    print(f"Generated images: {image_paths}.")

    bot = setup.get_bot()
    owner_id = setup.get_telegram_owner_id()

    for message in messages:
        bot.send_message(chat_id=owner_id, text=message)

    for image_path in image_paths:
        bot.send_photo(chat_id=owner_id, photo=open(image_path, "rb"))


def gcal(interval: utils.TriggerInterval):
    bot = setup.get_bot()
    owner_id = setup.get_telegram_owner_id()
    service = setup.get_calendar_service()
    start = utils.first_of_jan_timestamp(year=_FIRST_YEAR)
    end = utils.now_timestamp()

    for sport in utils.Sport:
        df = cal.get_dataframe(
            cal.get_filtered_events(
                service,
                start,
                end,
                "summary",
                filter_value=sport.value,
            )
        )

        if len(df) == 0 or not cal.has_time_relevant_event(df, interval=interval):
            print(
                f"No event for {interval.value} {sport.value} during this past time interval."
            )
            continue

        messages = [
            message_function(df)
            for message_function in cal.message_function_registry(sport, interval)
        ]
        print(f"Generated messages for {interval.value} {sport.value}: {messages}.")

        for message in filter(lambda x: x is not None and x != "", messages):
            bot.send_message(chat_id=owner_id, text=message)

        tmpdir = setup.get_tmpdir()
        image_paths = [
            image_function(df)
            for image_function in cal.image_function_registry(sport, interval, path=tmpdir)
        ]
        print(f"Generated images for {interval.value} {sport.value}: {image_paths}.")

        for image_path in filter(lambda x: x is not None, image_paths):
            bot.send_photo(chat_id=owner_id, photo=open(image_path, "rb"))


def main(request, context):
    kind = utils.parse_payload(request)
    if kind == "org":
        org_log()
    elif kind == "calendar":
        gcal(utils.TriggerInterval.daily)
    elif kind == "calendar_weekly":
        gcal(utils.TriggerInterval.weekly)
    else:
        raise ValueError(f"Unexpected kind of request: {kind}.")


if __name__ == "__main__":
    main("data", "context")
