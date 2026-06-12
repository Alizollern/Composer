import React from "react";

export default function Features() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
      <h1 className="text-4xl font-extrabold text-slate-900 mb-6">Возможности</h1>
      <p className="text-xl text-slate-600 mb-12 max-w-3xl">Всё, чтобы держать стандарты сети под контролем и быстро вводить новых людей в работу.</p>

      <div className="space-y-16">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Ответы строго по вашим документам</h2>
          <p className="text-slate-600 max-w-3xl">Evergreen отвечает только тем, что есть в загруженных стандартах, и всегда показывает источник. Нет правила в документе — система прямо скажет «такого нет», а не придумает ответ. Это и есть доверие.</p>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Разделение доступа по ролям</h2>
          <p className="text-slate-600 max-w-3xl">Управляйте тем, кто что видит. Документы для управляющих не попадут к рядовым сотрудникам, а стандарты конкретной точки увидят только её сотрудники. Система соблюдает эти границы в каждом ответе.</p>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Онбординг и проверка знаний</h2>
          <p className="text-slate-600 max-w-3xl">Соберите документы в учебные треки. Новый сотрудник проходит их и отвечает на автогенерируемые тесты прямо в системе — управляющий экономит часы на обучении, а вы видите, кто реально готов к смене.</p>
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Карта пробелов в знаниях</h2>
          <p className="text-slate-600 max-w-3xl">Система собирает вопросы, на которые в стандартах не нашлось ответа. Вы видите, чего не хватает в регламентах и что чаще всего спрашивает команда — и дорабатываете документы точечно.</p>
        </div>
      </div>
    </div>
  );
}
