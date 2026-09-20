# Arena: архитектура платформы и подключения участников

20 сентября 2026. Архитектурный RFC. Первый срез реализации уже выделен в этот репозиторий: каталог, реестр, локальный observer и Cloudflare Worker. Оркестрация, интеграция запуска фреймворков, развёртывание и платные прогоны ещё не выполнены. Актуальное состояние — в README.md. Этот документ заменяет прежний план размещения Arena внутри SCiEL.

## 1. Решение и границы

**Arena — самостоятельная платформа в отдельном репозитории.** Она владеет каталогом задач, контрактами сред и оценки, реестром участников, запуском экспериментов, хранением результатов и Board. SCiEL, ShinkaEvolve и позднее DGM — внешние участники, подключаемые из GitHub. Каждый сохраняет собственный алгоритм и состояние.

Board развивается из существующего dashboard SCiEL: переиспользуются подходящие интерфейсы и представления, но каталог и управление принадлежат Arena. SCiEL остаётся отдельным участником с подробными native views. Код платформы не размещается в `src/sciel/arena/` и не зависит от импорта Engine.

| ADR | Статус | Решение и следствие |
|---|---|---|
| A1 | Подтверждено пользователем | Arena и участники — независимые сущности; задачи и участники подключаются через GitHub-репозитории. |
| A2 | Подтверждено пользователем | Первая версия закрыта для команды; добавления проходят PR в общий реестр. Публичный marketplace не входит в v1. |
| A3 | Подтверждено пользователем | Cloudflare размещает платформу и Board, машина Vast.ai выполняет вычисления. |
| A4 | Подтверждено пользователем | Сначала обычный SCiEL и ShinkaEvolve; DGM подключается отдельным последующим этапом. |
| A5 | Рекомендация | Хранить `registry/` в репозитории Arena; PR связывает внешний пакет с точной версией и разрешённым профилем. |
| A6 | Рекомендация | Workers Static Assets + API, D1, R2; одна Vast VM с supervisor и Docker. Без Cloudflare Queues и Durable Objects в v1. |
| A7 | Рекомендация | Версия становится доступной после проверки; рекомендованная версия меняется отдельно через PR. Ни webhook, ни обновление версии не запускают исследование. |

## 2. Проверенные исходники и ограничения снимка

Это версии, на которых основан анализ, а не динамические ссылки на «самую новую» ветку. При реализации выбирается и проверяется новый точный lock; рабочие ветки продолжают меняться.

| Источник | Проверенный commit | Использование |
|---|---|---|
| `IMRUNya/autoresearch-tasks` | `995768fc462b8e327f90e6762846cc6ccb06cc2c` | Зарегистрировать существующий приватный репозиторий как `task_collection`; использовать задачи и evaluator. |
| SCiEL, worktree `sciel-packing-gallery` | `94debca936808d6eef829468b02892894e70e50f` | Подключать ordinary Engine, G/C/R, research tools, CLI и native dashboard. |
| `SakanaAI/ShinkaEvolve` | `9912af12d423504b8d580f4179fd15f5f88b8c50` | Native runner, evaluator adapter, архив и журналы. |
| `jennyzzt/dgm` | `a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2` | Отдельный Arena episodic adapter; исходные harness связаны с SWE-bench/Polyglot. |

Корневая рабочая копия `sciel` отличается от `sciel-packing-gallery`; реализовывать нужно от выбранного актуального снимка в отдельном worktree. Для невнесённых изменений необходим исходный bundle/tree hash: одного Git HEAD недостаточно.

В проверенном task repo 1 138 пакетов: 710 имеют исполняемый suite-протокол, 428 обозначены unsupported. Это инвентаризация снимка, а не число готовых экспериментов: наличие evaluator, готовность среды и совместимость участника проверяются раздельно.

`autoresearch_tasks/sciel_worker.py` импортирует `openevolve`, а tiny evolution выключает conclusions/reflection/KB и задаёт один island. Этот legacy wrapper не представляет полный текущий SCiEL и не становится его Arena adapter.

## 3. Компоненты и размещение

| Где | Компонент | Ответственность |
|---|---|---|
| Cloudflare Workers | Static Assets / Board | Каталог, настройка запусков, сравнения, визуализация сохранённых результатов. |
| Cloudflare Workers | Arena API | Авторизация, реестр, RunSpec, команды, приём событий, выдача ограниченных URL для артефактов. |
| Cloudflare D1 | Control database | Версии, immutable specs, очередь заданий, попытки, leases, inbox webhook, итоговые индексы и учёт бюджета. |
| Cloudflare R2 | Artifact storage | Исходные bundles, native logs, checkpoints, evaluation receipts, входы/выходы и результирующие manifests. |
| Vast VM | Supervisor | Исходящие обращения к API, сборка/проверка пакетов, admission ресурсов, запуск, остановка, heartbeat и синхронизация. |
| Vast VM / Docker | Participant runtime | Родной процесс SCiEL/Shinka/DGM с закреплённым adapter и окружением. |
| Vast VM / отдельный Docker sandbox | Evaluation service | Исполнение выбранного task protocol, изоляция кандидата, фиксация измерения и артефактов. |

API принимает решения о доступе и сохраняет намерение; supervisor владеет процессами. Вычисления, сборки Docker и научные evaluation выполняются на Vast. Workers не используются как длительно живущий Python-процесс: их лимиты и жизненный цикл HTTP не подходят для этого.

В v1 supervisor опрашивает очередь D1 через API по исходящему HTTPS; открытый входящий endpoint на Vast не нужен. Cloudflare Access защищает Board; worker получает отдельную machine identity с ограниченными правами. GitHub credential и ключи supervisor не передаются коду участника или кандидата.

D1 хранит небольшие записи состояния, R2 — большие неизменяемые объекты. Worker выдаёт короткоживущий presigned PUT/GET для конкретного объекта; supervisor передаёт данные напрямую в R2. Публикация результата происходит после загрузки и проверки полного artifact manifest.

Одна VM ограничивает доступность и параллелизм, но позволяет проверить весь протокол. Supervisor локально сохраняет spool и checkpoints; потеря VM может потерять ещё не выгруженный хвост. Периодическая выгрузка ограничивает эту потерю и должна быть проверена до длительных запусков.

## 4. Подключение через GitHub

Рекомендуемая структура: репозиторий платформы `arena` содержит `registry/tasks/`, `registry/participants/` и JSON schemas. Запись реестра ссылается на внешний repository и manifest. Репозиторий participant adapter может отдельно фиксировать upstream repository + commit; форк upstream не обязателен.

`autoresearch-tasks` регистрируется одной коллекцией с пакетом-индексом. Arena импортирует её каталог из зафиксированной версии; не поддерживает вручную вторую копию 1 138 задач. Новая коллекция задач и новый участник проходят одинаковый путь регистрации, но разные conformance checks.

Путь обновления: **PR реестра → review/merge → signed GitHub webhook → durable inbox → validation/build/conformance → available version**. Проверка подписи выполняется до обработки; delivery ID и repository/commit позволяют дедуплицировать доставку. После сохранения inbox Worker быстро отвечает GitHub, а supervisor выполняет длительную работу.

Валидация включает schema, доступность приватного commit, получение зависимостей, сборку image, соблюдение entrypoints и ограниченные проверки известных кандидатов. Это техническая проверка пакета, а не запуск исследовательского поиска. Расходы сборки/проверки отмечаются отдельно.

Версия идентифицируется неизменяемыми commit и digest. Branch/tag допустим как источник обнаружения, но не как lock запуска. Статусы: `discovered → validating → available|rejected`; recommendation — отдельная ссылка, изменяемая PR. Обновление recommendation не меняет запущенные или сохранённые RunSpec.

Совместимость определяется **task protocol × participant profile × environment capabilities**. Успешная регистрация не означает совместимость со всеми задачами. UI различает: evaluator существует, participant поддерживает контракт, среда собрана, conformance реально пройден с указанной версией и датой.

## 5. Контракты пакетов и запусков

| Контракт | Обязательные данные |
|---|---|
| `TaskManifest` / `TaskCollectionManifest` | ID задачи/семейства/протокола, условие, происхождение, candidate interface, seed/assets, evaluator entrypoint, raw metrics/direction, fitness transform, environment, ресурсы, seeds/repeats, search/audit policy, схемы артефактов. |
| `ParticipantManifest` | ID, adapter entrypoint/version, upstream source lock, поддерживаемые candidate/protocol types, native config schema, start/stop/resume capabilities, receipt/telemetry contract, image definition. |
| `EnvironmentManifest` | Image digest, runtime и численные библиотеки, CPU/GPU/RAM, threads, mounts, сеть, ограничения процессов, совместимые evaluator/participant profiles. |
| `VersionLock` | Repository/commit и tree/source bundle, manifest digest, adapter version, dependency locks, image digest, evaluator/data/assets hashes и runtime-конфигурация. |
| `RunSpec` | Все locks, native configuration, исходный кандидат, модели, search/evaluation seeds, протокол, отдельные пределы денег/времени/ресурсов/измерений и политика остановки. |
| `EvaluationReceipt` | Request/attempt identity, кандидат, все условия измерения, статус/validity, raw metrics, fitness/transform, ошибки, inputs/outputs refs, фактические ресурсы и стоимость с provenance. |

`problem_family_id` связывает близкие задачи для покрытия и development/audit split; название статьи само по себе не доказывает независимость. Suite/upstream/recreated evaluator остаются разными protocol versions.

`logical_run_id` сохраняется при поддерживаемом resume; новый процесс получает новый `attempt_id` и segment. Несовместимый protocol/engine/config создаёт новый run. Campaign — заранее закреплённая матрица задач, участников и независимых search seeds, а не интерактивная смена условий внутри run.

Не вводим общий `propose()/step()` для фреймворков. Adapter запускает полный родной процесс и переводит внешние контракты; алгоритм поиска остаётся у участника. Capabilities запрещают показывать Resume или lineage там, где они реально не поддерживаются.

## 6. Очередь, lease и восстановление

1. Авторизованный `POST /runs` с idempotency key сохраняет неизменяемый RunSpec и queued job в D1. Только явная команда запуска создаёт исследовательскую работу.
2. Supervisor запрашивает `/worker/claim` с idempotency key. Условный SQL update атомарно выдаёт `attempt_id`, растущий `lease_epoch` и срок; повтор запроса возвращает ту же выдачу. Сначала прочитать, затем безусловно обновить строку недостаточно; решения о владении используют primary state.
3. Heartbeat продлевает lease и получает команды. Начальные эксплуатационные параметры: раз в 15 секунд, expiry 90 секунд; это настраиваемая рекомендация, а не научный параметр.
4. Renew, события и finish содержат attempt/epoch; каждое событие имеет `(attempt_id, seq)` и payload hash. Повторы доставки идемпотентны, конфликтующие payload отклоняются. Локальный durable spool переживает перезапуск supervisor; R2 принимает immutable chunks.
5. Завершение проверяет актуальные attempt/epoch, сохранённые receipts и artifact manifest. Повтор того же finish digest безопасен; устаревший epoch не может заменить официальный результат. Поздние receipts старой попытки сохраняются как доказательства и учитываются в расходах, без восстановления права управления.
6. Истёкший lease переводит попытку в `orphaned/needs_reconciliation`, а не доказывает смерть процесса. Автоматически запускать второй оплачиваемый поиск нельзя. Старый supervisor при утрате lease прекращает новую работу, сохраняет результаты уже отправленных операций и останавливает потомков по политике.
7. Восстановление сначала устанавливает судьбу старого процесса и внешних запросов. Затем возможен resume из проверенного checkpoint; неопределённый вызов остаётся `unknown`. Fencing запрещает новые записи, но не отменяет уже отправленный LLM-запрос.
8. Stop сохраняет `cancel_requested`; supervisor прекращает новые работы, завершает/прерывает текущие по RunSpec, включая background tools, и выгружает checkpoint/receipts. При недоступной VM UI показывает ожидающую команду, а не выдуманный `stopped`.

Начальные состояния run: `queued → running → succeeded|failed|cancelled`, с `cancel_requested` и `needs_reconciliation` как явными промежуточными состояниями. Закрытие Board не меняет процесс. Terminal state не означает автоматически полный accounting: этот статус отдельный.

Cloudflare Queues и Durable Objects не нужны для одной VM. Если позднее потребуется Queues, сообщение будет уведомлением с job ID, D1 останется authority; доставка at-least-once требует дедупликации и transactional outbox. Visibility timeout сообщения не заменяет lease многочасового эксперимента.

## 7. Единая оценка и учёт

Единая оценка означает один закреплённый протокол и authority результата для выбранной задачи, а не одну универсальную формулу для всех наук. Evaluation service материализует task bundle и выполняет evaluator отдельно от изменяемого кода участника; control API никогда не импортирует candidate source.

Request содержит `evaluation_id`, candidate hash, task/protocol locks, seed/replicate, `search|audit`, условия и бюджет. Завершённый receipt неизменяем. Повторная доставка того же request ID возвращает тот же receipt; настоящее повторное измерение получает новый ID и расход бюджета. Сбой после отправки внешнего запроса не превращается в бесплатный retry.

Сохраняются исходный словарь evaluator, raw metric и направление, объявленный fitness, `valid: true|false|null`, ошибки и фактические outputs. Неизвестность не заменяется нулём или correctness. В v1 нет скрытого общего кэша между прогонами; stochastic repeats нельзя подменять чтением старого receipt.

Предел ресурсов распространяется на участника, evaluator, вспомогательные tools и дочерние процессы. Docker execution profile задаёт filesystem/network/resource policy; один subprocess timeout изоляцию не обеспечивает. Ресурсный admission выполняет supervisor, внутренний scheduler фреймворка остаётся родным.

Accounting фиксирует генерацию, repair, G/C/R, embeddings, meta-поиск, model-driven evaluator, retries и все DGM episodes. До внешнего dispatch сохраняются intent и reservation. Один call ID считается один раз; native ledger и proxy ledger сверяются, а не складываются повторно. Расходы суммируются по logical run через все attempts/resume. Полное покрытие модельного трафика проверяется conformance; неподконтрольные вызовы делают точный dollar-budget comparison недопустимым.

Отдельно показываются подтверждённые расходы, оценки, reservations, ошибки и `unknown`. Неуспешный вызов может стоить денег. USD модели и фактические расходы Vast учитываются раздельно; CPU/GPU/wall time превращаются в деньги только по объявленному тарифу и правилу распределения общей VM. Исчерпание бюджета или неопределённый остаток запрещает новые операции согласно RunSpec.

## 8. Участники: точки интеграции и обязательные исправления

### SCiEL

Adapter вызывает актуальные native CLI `run/resume/stop` и материализует `--tasks-root` с `task.yaml`, seed, assets и evaluator bridge. Сохраняются Engine, populations, G/C/R, cells, research tools и background jobs выбранного профиля. `sciel.methods` может стать отдельным участником/профилем, но не заменяет ordinary Engine.

Общий seam — `Engine._evaluate` в `src/sciel/engine/loop.py`, куда приходят и native research submissions. Receipt становится generic research artifact с точными условиями, inputs/outputs и ошибками. Circle26-specific `native_geometry` не расширяется на произвольные науки.

До подключения minimization и дорогих evaluator необходимы три изменения, подтверждённые текущим исходным кодом:

- `eval/_runner.py::_normalize` предпочитает top-level `score`; при таком ответе соседний top-level `combined_score` не выбирается. `{score: loss, combined_score: -loss}` заставит Engine максимизировать loss. Bridge передаёт объявленный fitness в engine score, raw loss хранит отдельно.
- Одного `-loss` недостаточно: relative refine в `engine/loop.py` сравнивает с `refine_elite_frac * max(pop_best, 1e-9)`, а `engine/db.py` использует `max(0, min(int(score * grid_bins), grid_bins - 1))`. Отрицательные scores попадают в нулевой score bin. Нужны знакоустойчивое правило refinement и явная шкала bins, без скрытой произвольной нормализации.
- `eval/cascade.py` выполняет smoke, затем full. Если обе стадии bridge вызывают одну дорогую Arena-оценку, получится два физических измерения. Объявить дешёвый preflight + одну full-оценку либо поддержать одностадийный план; подлинные confirm/repeats учитывать отдельно.

Native `B_evals` и число принятых программ не равны общему числу физических evaluations. Arena считает seed, failed, повторные и вспомогательные измерения по receipts, сохраняя родные счётчики отдельно.

### ShinkaEvolve

Adapter сохраняет native `ShinkaEvolveRunner`, архив, islands, parent selection, patch operators и model/meta-компоненты выбранного профиля. Bridge для `LocalJobConfig(eval_program_path=...)` принимает `--program_path`/`--results_dir`, вызывает общий evaluator и записывает `metrics.json`, `correct.json` и receipt ref. `combined_score` получает объявленный fitness; политика mapping неизвестной validity задана заранее, иначе профиль не допускается.

Не добавляется независимая повторная проверка задачи или скрытый `run_shinka_eval` поверх уже выполненной оценки. Board читает native `programs.sqlite` и журналы через projection adapter, не создавая вымышленные SCiEL events. Наличие upstream resume не доказывает безопасный resume Arena: pending evaluations и accounting проверяются отдельно.

### DGM-on-Arena

DGM изменяет реализацию агента, а не только программу-решение. Нужен явный Arena episodic adapter: **agent revision → task episode → candidate programs → evaluation receipts → development fitness агента**. Agent revision фиксирует base commit, упорядоченные patches, итоговый tree hash, зависимости и model config. Evaluator и принудительные лимиты находятся вне изменяемого agent tree.

Сначала подключается frozen agent revision к ограниченному набору поддержанных протоколов; затем native outer archive/parent selection и саморедактирование. Нужны `ArenaEpisodeRunner`, Arena fitness aggregation и diagnosis. Исходные SWE/Polyglot harness, accuracy thresholds и сохранённые baseline scores нельзя автоматически перенести на Arena. Совместимость с каждой task family доказывает episode conformance.

Сравниваются два разных experiment types: frozen agent решает задачи с фиксированным inference budget, раскрывая стоимость предварительной эволюции; outer-loop evolution учитывает полную стоимость создания ревизий и всех вложенных эпизодов. Их результаты не смешиваются в одной безусловной таблице «цена поиска».

Development и финальный audit разделены по семействам задач; память между эпизодами допускается только протоколом. Audit feedback не возвращается в self-improvement. Это относится и к diagnosis: upstream SWE prompts используют `test_patch` и логи development-примера; закрытые финальные данные в Arena diagnosis недоступны. Несопоставимые raw scores разных задач не усредняются без закреплённого правила.

## 9. Board и сравнения

Board показывает каталог и readiness, версии и совместимые профили, RunSpec, очередь, управление через API, результаты и Compare. Общая RunView содержит identities, состояние с доказательствами живости, raw score/direction, стоимость, wall time, физические evaluations, ошибки и полноту accounting. Iteration/generation остаются родными счётчиками.

Каждая точка кривой ведёт к candidate source, receipt и artifact manifest. Native journals остаются первичными; projections имеют source refs/cursors и повторяемый импорт. Для SCiEL доступны G/C/R, populations, cells/tools/jobs; другим участникам не приписываются отсутствующие возможности. Исторический импорт read-only, пока adapter не подтвердил управляемость и владение процессом.

Artifact renderers привязаны к схемам: геометрия, таблицы, временные ряды, prediction/residual, сертификаты. Страница показывает сохранённое; открытие страницы ничего не пересчитывает. Отсутствующая траектория не восстанавливается из конечной точки без нового явного измерения.

Compare допускает только согласованные task/protocol/data versions, budgets и условия. Общий набор моделей и полные native multi-model системы — разные режимы. Показываются independent seeds, failures, coverage и ограничения. Evaluator, раскрывающий test metric во время поиска, не объявляется независимым audit; для audit нужен отдельный версионированный протокол.

## 10. Этапы и критерии готовности

| Этап | Поставляемый результат | Приёмка |
|---|---|---|
| 1. Основание Arena | Отдельный repo, schemas/registry, GitHub inbox, D1/R2/API, Board catalog | PR приватной коллекции и participant создаёт проверенную available version; повтор webhook не дублирует build; recommendation и research launch не меняются сами. |
| 2. Исполнение и оценка | Одна Vast VM, Docker supervisor, leases, evaluator, receipts/accounting | Фиксированные valid/invalid/timeout кандидаты проходят объявленный протокол; повтор claim/receipt/finish идемпотентен; disconnect/lease expiry не создаёт второй оплачиваемый процесс. |
| 3. Native SCiEL | Adapter обычного Engine, minimization fixes, generic research receipts, native views | Raw loss/fitness корректны, отрицательные scores не ломают selection/bins; cascade не дублирует дорогое измерение; research submission идёт тем же путём. |
| 4. Native Shinka и сравнение | Adapter, projections, campaigns, Compare | Один кандидат при фиксированных условиях оценивается одним протоколом; стохастические различия учитываются повторами; архив родной, учёт полон, stop/resume сверяет pending операции. |
| 5. DGM-on-Arena | Frozen episodes, затем outer-loop profile | Явная матрица поддержанных задач, отдельные agent/program lineage, полный inner/outer cost и недоступность audit feedback для эволюции. |

Первый набор conformance: геометрическая конструкция, минимизация ошибки регрессии, численный метод — только после выбора конкретных совместимых protocol IDs. Сначала проверки известных кандидатов без исследовательской генерации; затем отдельные ограниченные pilots с назначенными моделями и бюджетами. Один pilot проверяет интеграцию, но не превосходство метода.

Демо v1: команда регистрирует GitHub task/participant через PR; в Board выбирает доступную задачу, SCiEL и Shinka, фиксирует условия и запускает два native процесса. Любой результат раскрывает точный код, протокол, артефакты и расходы; закрытие браузера не влияет на работу.

## Источники

- [Task interface, закреплённый снимок](https://github.com/IMRUNya/autoresearch-tasks/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/docs/INTERFACE.md); [legacy SCiEL wrapper](https://github.com/IMRUNya/autoresearch-tasks/blob/995768fc462b8e327f90e6762846cc6ccb06cc2c/src/autoresearch_tasks/sciel_worker.py).
- [ShinkaEvolve: evaluator/resume](https://github.com/SakanaAI/ShinkaEvolve/blob/9912af12d423504b8d580f4179fd15f5f88b8c50/docs/getting_started.md); [native API](https://sakanaai.github.io/ShinkaEvolve/reference/core_api/).
- [DGM outer loop](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/DGM_outer.py); [task orchestration](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/self_improve_step.py); [diagnostic context](https://github.com/jennyzzt/dgm/blob/a565fd2d1dca504ef5104a7cc0f3bdc4ab9b4fd2/prompts/self_improvement_prompt.py).
- [Workers Static Assets](https://developers.cloudflare.com/workers/static-assets/) и [runtime limits](https://developers.cloudflare.com/workers/platform/limits/); [D1 transactional batch](https://developers.cloudflare.com/d1/worker-api/d1-database/) и [read replication](https://developers.cloudflare.com/d1/best-practices/read-replication/).
- [R2 presigned URLs](https://developers.cloudflare.com/r2/api/s3/presigned-urls/); [Access service tokens](https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/); [Queues delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/).
- Локальные SCiEL seams: `sciel-packing-gallery/src/sciel/web/{server,data}.py`, `eval/{registry,_runner,cascade}.py`, `engine/{loop,db,runtime}.py`, `cli/main.py`. Проверка конкретных исходников повторяется перед реализацией adapter.
