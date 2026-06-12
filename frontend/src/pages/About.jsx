import React from "react";

export default function About() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
      <h1 className="text-4xl font-extrabold text-slate-900 mb-6">О Evergreen</h1>
      <p className="text-xl text-slate-600 mb-12 max-w-2xl mx-auto">
        Мы верим, что стандарты компании не должны пылиться в PDF-файлах и теряться в чатах. Они должны быть живыми, доступными и работать на каждой смене.
      </p>

      <div className="text-left space-y-8 bg-slate-50 p-8 rounded-2xl border border-slate-200">
        <div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Наша миссия</h3>
          <p className="text-slate-600">Помочь сетевому бизнесу расти без потери качества. Мы превращаем статичные регламенты в цифрового двойника руководителя, который держит всю команду в едином стандарте — от первой точки до сотой.</p>
        </div>
        <div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Наша история</h3>
          <p className="text-slate-600">Мы строим Evergreen для растущих сетей Казахстана — фитнеса, общепита, ритейла, услуг. Начали с реальной боли: каждый новый сотрудник задаёт одни и те же вопросы, а стандарты живут только в голове основателя. Evergreen переносит их в систему — раз и навсегда.</p>
        </div>
      </div>
    </div>
  );
}
