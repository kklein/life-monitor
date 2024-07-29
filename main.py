import asyncio

from monitoring import cal, org, setup, utils

_FIRST_YEAR = 2022


async def send_message(bot, chat_id, message):
    await bot.send_message(chat_id=chat_id, text=message)


async def send_messages(bot, chat_id, messages):
    async with bot:
        tasks = [send_message(bot, chat_id, message) for message in messages]
        await asyncio.gather(*tasks)


async def send_photo(bot, chat_id, photo):
    await bot.send_photo(chat_id=chat_id, photo=photo)


async def send_photos(bot, chat_id, photos):
    async with bot:
        tasks = [send_photo(bot, chat_id, photo) for photo in photos]
        await asyncio.gather(*tasks)


def org_log(interval: utils.TriggerInterval):
    weeks_dir = setup.create_and_get_week_dir()
    df = org.load_data(week_root=weeks_dir, first_weekday_index=3)
    df = org.process_data(df)

    if interval == utils.TriggerInterval.weekly:
        messages = org.messages_this_week(df)
        image_paths = org.images_this_week(df, path=weeks_dir)
    elif interval == utils.TriggerInterval.daily:
        messages = org.messages_this_day(df)
        image_paths = []
    else:
        raise ValueError(f"Unexpected TriggerInterval for org_log: {interval}.")

    print(f"Generated messages: {messages}.")
    print(f"Generated images: {image_paths}.")

    bot = setup.get_bot()
    owner_id = setup.get_telegram_owner_id()

    asyncio.run(send_messages(bot, owner_id, messages))
    asyncio.run(
        send_photos(
            bot, owner_id, (open(image_path, "rb") for image_path in image_paths)
        )
    )


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
                filter_value=sport,
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

        messages = filter(lambda x: x is not None and x != "", messages)

        asyncio.run(send_messages(bot, owner_id, messages))

        tmpdir = setup.get_tmpdir()
        image_paths = [
            image_function(df)
            for image_function in cal.image_function_registry(
                sport, interval, path=tmpdir
            )
        ]
        print(f"Generated images for {interval.value} {sport.value}: {image_paths}.")

        image_paths = filter(lambda x: x is not None, image_paths)

        asyncio.run(
            send_photos(
                bot, owner_id, (open(image_path, "rb") for image_path in image_paths)
            )
        )


def main(request, context):
    kind = utils.parse_payload(request)
    if kind == "org_daily":
        org_log(utils.TriggerInterval.daily)
    elif kind == "org_weekly":
        org_log(utils.TriggerInterval.weekly)
    elif kind == "calendar_daily":
        gcal(utils.TriggerInterval.daily)
    elif kind == "calendar_weekly":
        gcal(utils.TriggerInterval.weekly)
    else:
        raise ValueError(f"Unexpected kind of request: {kind}.")


if __name__ == "__main__":
    main("data", "context")
