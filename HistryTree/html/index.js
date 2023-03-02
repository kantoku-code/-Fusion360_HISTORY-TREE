let DEBUG = false

document.addEventListener("DOMContentLoaded", () => {
	let adskWaiter = setInterval(() => {
		if (window.adsk) {
			clearInterval(adskWaiter);

			adsk.fusionSendData("htmlLoaded", "").then((data) => {
			let infos = JSON.parse(data);
			dump(infos)
			$("#tree").jstree(true).settings.core.data = infos.data;
			$("#tree").jstree(true).refresh();
			}, 100);
		}
	});
});

function dump(s) {
	if (DEBUG) {
		console.log(s);
	}
}

$("#tree").jstree({
	core: {
		multiple: false,
		themes: { stripes: true },
		data: [
			{
				text: "Loading...",
				icon: "fal fa-broadcast-tower",
			},
		],
	},
	plugins: ["search"],
//   plugins: ["search", "contextmenu"],
//   contextmenu: {
//     items: function ($node) {
//     return {
//       open_active: {
//       separator_before: false,
//       separator_after: false,
//       label: "オープン/アクティブ",
//       _disabled: function (data) {},
//       action: function (data) {
//         var inst = $.jstree.reference(data.reference),
//         obj = inst.get_node(data.reference);
//         var args = {
//         id: obj.id,
//         };
//         adsk.fusionSendData("open_active", JSON.stringify(args));
//       },
//       },
//     };
//     },
//   },
	});

	var to = false;
	$("#search-input").keyup(function () {
		if (to) {
			clearTimeout(to);
		}
		to = setTimeout(function () {
			var v = $("#search-input").val();
			$("#tree").jstree(true).search(v);
		}, 250);
	});