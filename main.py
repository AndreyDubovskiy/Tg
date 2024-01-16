import classes.SubprocessController
import classes.TgBotConfigurator
import asyncio

loop = asyncio.get_event_loop()

controller = classes.SubprocessController.SubprocessController()

tg = classes.TgBotConfigurator.TgBotConfigurator(subprocess_controller=controller)
tg.start()
loop.run_forever()