(function () {
  'use strict';

  var currentFile = window.location.pathname.split('/').pop() || '';
  var currentMatch = currentFile.match(/^(\d+)medtrace\.html$/i);
  var currentPage = currentMatch ? Number(currentMatch[1]) : 1;
  var transitionDuration = 240;

  var routes = {
    '1:.btn-create-account': 2,
    '2:.btn-submit': 3,
    '3:.btn-verify': 5,
    '4:.btn-login': 5,
    '5:.btn-continue': 6,
    '6:.btn-continue': 7,
    '8:.btn-continue': 9,
    '9:.btn-submit': 10,
    '10:.btn-share': 11,
    '10:.btn-view-profile': 12,
    '11:.btn-show-qr': 10,
    '13:.btn-reject': 14,
    '13:.btn-approve': 14,
    '15:.btn-login': 16,
    '18:.btn-request': 19,
    '19:.btn-send': 20,
    '20:.btn-dashboard': 16,
    '21:.btn-done': 22,
    '22:.btn-continue': 23,
    '23:.btn-done': 24,
    '24:.btn-done': 1
  };

  var patientMenuRoutes = [11, 12, 10, 23, 14];
  var providerMenuRoutes = [16, 18, 17, 19, 14];

  function getRoute(element) {
    var classNames = element.className && typeof element.className === 'string'
      ? element.className.split(/\s+/)
      : [];

    for (var i = 0; i < classNames.length; i += 1) {
      var route = routes[currentPage + ':.' + classNames[i]];
      if (route) {
        return route;
      }
    }

    return currentPage < 24 ? currentPage + 1 : 1;
  }

  function goToPage(page) {
    var destination = page + 'medtrace.html';
    document.body.classList.add('is-leaving');
    window.setTimeout(function () {
      window.location.href = destination;
    }, transitionDuration);
  }

  function goToHref(href) {
    var destination = new URL(href, window.location.href);
    if (destination.origin !== window.location.origin) {
      return false;
    }

    document.body.classList.add('is-leaving');
    window.setTimeout(function () {
      window.location.href = destination.href;
    }, transitionDuration);
    return true;
  }

  var style = document.createElement('style');
  style.textContent =
    'body{opacity:0;transform:translateY(8px);transition:opacity ' + transitionDuration +
    'ms ease,transform ' + transitionDuration + 'ms ease;}' +
    'body.is-ready{opacity:1;transform:translateY(0);}' +
    'body.is-leaving{opacity:0;transform:translateY(-8px);}' +
    '@media (prefers-reduced-motion:reduce){body{transition:none!important;transform:none!important;}}';
  document.head.appendChild(style);

  document.addEventListener('DOMContentLoaded', function () {
    window.requestAnimationFrame(function () {
      document.body.classList.add('is-ready');
    });

    document.querySelectorAll('button').forEach(function (button) {
      if (
        button.classList.contains('toggle-password') ||
        button.classList.contains('btn-add-contact') ||
        button.classList.contains('btn-add-another') ||
        button.classList.contains('btn-add-procedure')
      ) {
        return;
      }

      button.addEventListener('click', function (event) {
        event.preventDefault();
        goToPage(getRoute(button));
      });
    });

    document.querySelectorAll('a.nav-item').forEach(function (link, index) {
      var menuRoutes = currentPage >= 25 && currentPage <= 29
        ? patientMenuRoutes
        : providerMenuRoutes;
      var destination = menuRoutes[index];

      if (destination) {
        link.addEventListener('click', function (event) {
          event.preventDefault();
          goToPage(destination);
        });
      }
    });

    document.querySelectorAll('a[href$="medtrace.html"]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        if (goToHref(link.href)) {
          event.preventDefault();
        }
      });
    });

    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
      });
    });
  });
}());
